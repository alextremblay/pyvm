#!/bin/bash
# region preamble
""":"
set -euo pipefail

# These values will have to be hard-coded for now until i find a better way to aquire them within this limited bash context
SELF_PY_VERSION=3.12.2
SELF_RELEASE_DATE=20240224

# bootstrap self
export PYVM_HOME=${PYVM_HOME:-$HOME/.pyvm}
mkdir -p $PYVM_HOME/tmp

if [ -f "$PYVM_HOME/3.12/bin/python3.12" ]; then
    exec "$PYVM_HOME/3.12/bin/python3.12" "$0" "$@"
fi

# define a function which selects curl or wget based on availability
download() {
    if command -v curl &> /dev/null; then
        curl -s -L -o $1 $2
    elif command -v wget &> /dev/null; then
        wget -q -O $1 $2
    else
        echo "Neither curl nor wget found. Please install one of these packages."
        exit 1
    fi
}

case `uname -m` in
    x86_64)
        ARCH=x86_64_v3
        ;;
    arm64|aarch64)
        ARCH=aarch64
        ;;
    *)
        echo "Unsupported architecture: `uname -m`"
        exit 1
        ;;
esac

case `uname` in
    Linux)
        SUFFIX=unknown-linux-gnu-install_only.tar.gz
        ;;
    Darwin)
        SUFFIX=apple-darwin-install_only.tar.gz
        ;;
    *)
        echo "Unsupported OS: `uname`"
        exit 1
        ;;
esac

# download and install python
echo "bootstrapping with python 3.12..."
archive="cpython-${SELF_PY_VERSION}+${SELF_RELEASE_DATE}-${ARCH}-${SUFFIX}"
download "$PYVM_HOME/tmp/$archive" "https://github.com/indygreg/python-build-standalone/releases/download/${SELF_RELEASE_DATE}/${archive}"
pushd $PYVM_HOME/tmp
echo "extracting python 3.12..."
tar -xvf "$archive" > /dev/null
mv "$PYVM_HOME/tmp/python" "$PYVM_HOME/3.12"
popd
rm -rf $PYVM_HOME/tmp

exec "$PYVM_HOME/3.12/bin/python3.12" "$0" "$@"
"""
# endregion

# ruff: noqa: E401 EXE003 A001
import os

__doc__ = f"""Python Version Manager

This tool is designed to download and install python versions from the 
https://github.com/indygreg/python-build-standalone project into {os.environ.get('PYVM_HOME', '$HOME/.pyvm')}
and add versioned executables (ie `python3.12` for python 3.12) into a directory on the PATH.

Environment Variables:
    PYVM_HOME: The directory to install python versions into. Defaults to $HOME/.pyvm
    PYVM_BIN: The directory to install versioned executables into. Defaults to $HOME/.local/bin
    PYVM_PBS_RELEASE: The release of python-build-standalone to target. Defaults to 'latest', can be set to a release name (eg '20240224')
    PYVM_PIPX_RELEASE: The release of pipx to target. Defaults to 'latest', can be set to a release name (eg '1.5.0')
    PYVM_PIPX_DEFAULT_PYTHON_VERSION: The default python version to use when installing pipx onto your PATH. Defaults to '3.12'
"""
import sys
import argparse
import datetime
import hashlib
import json
import logging
import platform
import re
import shutil
import tarfile
import tempfile
import subprocess
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Literal, TYPE_CHECKING
import urllib.error
from urllib.request import urlopen


if TYPE_CHECKING:
    from typing import overload

    @overload
    def _fetch(url: str, type: Literal["json"]) -> dict | list: ...
    @overload
    def _fetch(url: str, type: Literal["file"]) -> bytes: ...
    @overload
    def _fetch(url: str, type: Literal["checksum"]) -> str: ...


# Much of the code in this module is adapted with extreme gratitude from
# https://github.com/tusharsadhwani/yen/blob/main/src/yen/github.py

MACHINE_SUFFIX: Dict[str, Dict[str, Any]] = {
    "Darwin": {
        "arm64": "aarch64-apple-darwin-install_only.tar.gz",
        "x86_64": "x86_64-apple-darwin-install_only.tar.gz",
    },
    "Linux": {
        "aarch64": {
            "glibc": "aarch64-unknown-linux-gnu-install_only.tar.gz",
            # musl doesn't exist
        },
        "x86_64": {
            "glibc": "x86_64_v3-unknown-linux-gnu-install_only.tar.gz",
            "musl": "x86_64_v3-unknown-linux-musl-install_only.tar.gz",
        },
    },
    "Windows": {"AMD64": "x86_64-pc-windows-msvc-shared-install_only.tar.gz"},
}

GITHUB_API_URL = (
    "https://api.github.com/repos/indygreg/python-build-standalone/releases"
)
PIPX_API_URL = "https://api.github.com/repos/pypa/pipx/releases"
PYTHON_VERSION_REGEX = re.compile(r"cpython-(\d+\.\d+\.\d+)")

WINDOWS = platform.system() == "Windows"
PYVM_HOME = Path(os.environ.get("PYVM_HOME", os.path.join(os.environ["HOME"], ".pyvm")))
PYVM_TMP = PYVM_HOME / "tmp"
PYVM_BIN = Path(
    os.environ.get("PYVM_BIN", os.path.join(os.environ["HOME"], ".local/bin"))
)
PYVM_PBS_RELEASE = os.environ.get("PYVM_PBS_RELEASE", "latest")
PYVM_PIPX_RELEASE = os.environ.get("PYVM_PIPX_RELEASE", "latest")
PYVM_PIPX_DEFAULT_PYTHON_VERSION = os.environ.get("PYVM_PIPX_DEFAULT_PYTHON_VERSION", "3.12")


class override:
    """Helper class to temporarily override module-level variables."""
    # TODO: there has got to be a better way to do this

    def __init__(self):
        pass

    def __enter__(self):
        self.GITHUB_API_URL = GITHUB_API_URL
        self.PIPX_API_URL = PIPX_API_URL
        self.PYTHON_VERSION_REGEX = PYTHON_VERSION_REGEX
        self.PYVM_HOME = PYVM_HOME
        self.PYVM_TMP = PYVM_TMP
        self.PYVM_BIN = PYVM_BIN
        self.PYVM_PBS_RELEASE = PYVM_PBS_RELEASE
        self.PYVM_PIPX_RELEASE = PYVM_PIPX_RELEASE
        self.PYVM_PIPX_DEFAULT_PYTHON_VERSION = PYVM_PIPX_DEFAULT_PYTHON_VERSION

    def __exit__(self, *args):
        global GITHUB_API_URL, PIPX_API_URL, PYTHON_VERSION_REGEX, PYVM_HOME, PYVM_TMP, PYVM_BIN
        global PYVM_PBS_RELEASE, PYVM_PIPX_RELEASE, PYVM_PIPX_DEFAULT_PYTHON_VERSION
        GITHUB_API_URL = self.GITHUB_API_URL
        PIPX_API_URL = self.PIPX_API_URL
        PYTHON_VERSION_REGEX = self.PYTHON_VERSION_REGEX
        PYVM_HOME = self.PYVM_HOME
        PYVM_TMP = self.PYVM_TMP
        PYVM_BIN = self.PYVM_BIN
        PYVM_PBS_RELEASE = self.PYVM_PBS_RELEASE
        PYVM_PIPX_RELEASE = self.PYVM_PIPX_RELEASE
        PYVM_PIPX_DEFAULT_PYTHON_VERSION = self.PYVM_PIPX_DEFAULT_PYTHON_VERSION


class NotAvailable(Exception):
    """Raised when the asked Python version is not available."""


logger = logging.getLogger(__name__)


def list_installed_versions():
    installations_found = False
    for major_minor, path in _installed_versions():
        msg = f"python{major_minor} is installed"
        _ensure_shim(path, major_minor)
        logger.info(msg)
        installations_found = True
    if not installations_found:
        logger.info("No python installations installed through pyvm")


def list_available_versions():
    pythons = _list_pythons()
    installed_pythons = [major_minor for major_minor, _ in _installed_versions()]
    logger.info("Available python versions:")
    pythons = [version.split(".") for version in pythons]
    pythons = sorted(pythons, key=lambda version: [int(k) for k in version])
    for version in pythons:
        major, minor, patch, *_ = version
        msg = f"{major}.{minor:2} --> {major}.{minor}.{patch}"
        if f"{major}.{minor}" in installed_pythons:
            msg += " (installed)"
        logger.info(msg)


def install_version(version: str):
    """Install the given python version and return the path to the python binary."""
    version = _normalize_python_version(version)
    if python_bin := _installed_version(version):
        logger.warning(f"Python version {version} is already installed")
        return python_bin
    logger.info(f"Installing python {version}...")
    python_bin = _download_python_build_standalone(version)
    _ensure_shim(python_bin, version)
    return python_bin


def ensure_version(version: str):
    """Ensure that the given python version is installed and return the path to the python binary."""
    version = _normalize_python_version(version)
    if python_bin := _installed_version(version):
        return python_bin
    else:
        return _download_python_build_standalone(version)


def uninstall_version(version: str):
    version = _normalize_python_version(version)
    _uninstall_version(version)
    _remove_shim(version)


def update_all_versions():
    maybe_update_pipx()
    available_pythons = _list_pythons()
    available_pythons = {".".join(v.split(".")[:2]): v for v in available_pythons}
    for major_minor, path in _installed_versions():
        version = subprocess.check_output([path, "--version"]).decode().split()[1]
        if (
            major_minor in available_pythons
            and version != available_pythons[major_minor]
        ):
            _uninstall_version(major_minor)
            _remove_shim(major_minor)
            logger.info(
                f"Updating python {major_minor} from {version} to {available_pythons[major_minor]}..."
            )
            python_bin = _download_python_build_standalone(major_minor)
            _ensure_shim(python_bin, major_minor)


def maybe_update_pipx():
    "Update pipx, but only if it's already been downloaded"
    pipx_zipapp = PYVM_HOME / "pipx.pyz"
    if pipx_zipapp.exists():
        logger.info("Updating pipx...")
        download_pipx()


def download_pipx():
    # step one: get the latest release of pipx
    # TODO: a lot of this logic is pulled from _get_github_release_assets. i should refactor that function to be more generic
    url = PIPX_API_URL
    if PYVM_PIPX_RELEASE == "latest":
        url += "/latest"
    release_data = _fetch(url, "json")
    if PYVM_PIPX_RELEASE != "latest":
        release_data = [
            release
            for release in release_data
            if release["tag_name"] == PYVM_PIPX_RELEASE
        ]
        if not release_data:
            raise Exception(f"Unable to find pipx release {PYVM_PIPX_RELEASE}.")
        release_data = release_data[0]
    pyz_download_url = [
        asset["browser_download_url"]
        for asset in release_data["assets"] # type: ignore
        if asset["name"].endswith(".pyz")
    ][0]
    _download("pipx.pyz", pyz_download_url, PYVM_HOME / "pipx.pyz")
    return PYVM_HOME / "pipx.pyz"


def ensure_pipx():
    """Ensure that pipx is installed and return the path to the pipx zipapp."""
    pipx_zipapp = PYVM_HOME / "pipx.pyz"
    if pipx_zipapp.exists():
        return pipx_zipapp
    logger.info("Aquiring pipx...")
    pipx_zipapp = download_pipx()
    return pipx_zipapp


def install_pipx():
    """Download the pipx zipapp into PYVM_HOME and install a shim into PYVM_BIN."""
    pipx_zipapp = ensure_pipx()
    default_python = ensure_version(PYVM_PIPX_DEFAULT_PYTHON_VERSION)
    shim = PYVM_BIN / "pipx"
    if not shim.exists():
        logger.info(f"Creating shim for pipx at {shim}")
        shim.write_text(f'#!/bin/sh\nexec {default_python} {pipx_zipapp} "$@"\n')
        shim.chmod(0o755)
    return shim


def _installed_versions():
    for installed_version in PYVM_HOME.glob("3.*/bin"):
        major_minor = installed_version.parent.name
        installed_bin = installed_version / f"python{major_minor}"
        yield major_minor, installed_bin


def _installed_version(version: str):
    for major_minor, installed_bin in _installed_versions():
        if major_minor == version:
            return installed_bin
    return None


def _uninstall_version(version: str):
    if not _installed_version(version):
        logger.warning(f"Python version {version} is not installed")
        return
    shutil.rmtree(PYVM_HOME / version)
    logger.info(f"Uninstalled python {version}")


def _ensure_shim(path: Path, version: str):
    """Ensure that the python binary is available in the pyvm bin directory"""
    # This needs to be a shim, rather than a symlink, for reasons explained in the README,
    # under heading `## Why a shim, and not a symlink?`
    # The shim sets the TERMINFO_DIRS environment variable to include most common terminfo directories
    # as a workaround to https://gregoryszorc.com/docs/python-build-standalone/main/quirks.html#backspace-key-doesn-t-work-in-python-repl
    _ensure_pyvm_bin_dir()
    shim = Path(PYVM_BIN / f"python{version}")
    if not shim.exists():
        logger.info(f"Creating shim for {version} at {shim}")
        shim.write_text(f'#!/bin/sh\nexec {path} "$@"\n')
        shim.chmod(0o755)
    return shim


def _ensure_pyvm_bin_dir():
    Path(PYVM_BIN).mkdir(parents=True, exist_ok=True)
    for bin_dir in os.environ["PATH"].split(os.pathsep):
        if PYVM_BIN.samefile(bin_dir):
            return
    else:
        logger.warning(f"Please add {PYVM_BIN} to your PATH")
        logger.warning(
            f"Ex, add the following to your shell profile: export PATH=$PATH:{PYVM_BIN}"
        )


def _remove_shim(version: str):
    # only remove the shim if it points to the version we're uninstalling
    shim = PYVM_BIN / f"python{version}"
    path = _installed_version(version)
    if not path:
        return
    if str(path) in shim.read_text():
        shim.unlink()
        logger.info(f"Removed {shim}")


def _normalize_python_version(python_version: str) -> str:
    # python_version can be a bare version number like "3.9" or a "binary name" like python3.10
    # we'll convert it to a bare version number
    return re.sub(r"[c]?python", "", python_version)


def _download_python_build_standalone(python_version: str):
    """Attempt to download and use an appropriate python build
    from https://github.com/indygreg/python-build-standalone
    and unpack it into the PYVM_HOME directory.
    Returns the full path to the python binary within that build"""

    install_dir = PYVM_HOME / python_version
    installed_python = (
        install_dir / "python.exe" if WINDOWS else install_dir / "bin" / "python3"
    )

    if installed_python.exists():
        return installed_python

    if install_dir.exists():
        logger.warning(
            f"A previous attempt to install python {python_version} failed. Retrying."
        )
        shutil.rmtree(install_dir)

    try:
        full_version, download_link = _resolve_python_version(python_version)
    except NotAvailable as e:
        raise Exception(
            f"Unable to acquire a standalone python build matching {python_version}."
        ) from e

    with tempfile.TemporaryDirectory() as tempdir:
        archive = Path(tempdir) / f"python-{full_version}.tar.gz"
        download_dir = Path(tempdir) / "download"

        # download the python build gz
        _download(f"python {full_version} build", download_link, archive)

        # unpack the python build
        _unpack(full_version, download_link, archive, download_dir)

        # the python installation we want is nested in the tarball
        # under a directory named 'python'. We move it to the install
        # directory
        extracted_dir = download_dir / "python"
        shutil.move(extracted_dir, install_dir)

    return installed_python


def _download(what: str, from_url: str, to_path: Path):
    logger.info(f"Downloading {what}")
    try:
        to_path.write_bytes(_fetch(from_url, "file"))

    except urllib.error.URLError as e:
        raise Exception(f"Unable to download {what}.") from e


def _fetch(url, type: Literal["json", "file", "checksum"]):
    # A single mockable function to fetch json, files, or checksums from github
    if type == "json":
        with urlopen(url) as response:
            return json.load(response)
    elif type == "file":
        # python standalone builds are typically ~32MB in size. to avoid
        # ballooning memory usage, we read the file in chunks
        res = tempfile.TemporaryFile()
        with urlopen(url) as response:
            for data in iter(partial(response.read, 32768), b""):
                res.write(data)
        res.seek(0)
        return res.read()
    elif type == "checksum":
        return urlopen(url).read().decode().rstrip("\n")
    else:
        raise ValueError(
            f"Argumen `type` must be one of ['json', 'file', 'checksum'], not {type}"
        )


def _unpack(full_version, download_link, archive: Path, download_dir: Path):
    logger.info(f"Unpacking python {full_version} build")
    # Calculate checksum
    with open(archive, "rb") as python_zip:
        checksum = hashlib.sha256(python_zip.read()).hexdigest()

    # Validate checksum
    checksum_link = download_link + ".sha256"
    expected_checksum = _fetch(checksum_link, "checksum")
    if checksum != expected_checksum:
        raise Exception(
            f"Checksum mismatch for python {full_version} build. "
            f"Expected {expected_checksum}, got {checksum}."
        )

    with tarfile.open(archive, mode="r:gz") as tar:
        tar.extractall(download_dir)


def _get_or_update_index():
    """Get or update the index of available python builds from
    the python-build-standalone repository."""
    index_file = PYVM_HOME / "index.json"
    write_cache = True
    if index_file.exists():
        index = json.loads(index_file.read_text())
        # update index after 5 days
        fetched = datetime.datetime.fromtimestamp(index["fetched"])
        if datetime.datetime.now() - fetched > datetime.timedelta(days=5):
            index = {}
    else:
        index = {}
    if PYVM_PBS_RELEASE != "latest":
        # we don't want to use the cache if we're targeting a specific release
        index = {}
        write_cache = False
    if not index:
        assets = _get_github_release_assets()
        index = {"fetched": datetime.datetime.now().timestamp(), "assets": assets}
        # update index
        index_file.parent.mkdir(parents=True, exist_ok=True)
        if write_cache:
            index_file.write_text(json.dumps(index))
    return index


def _get_github_release_assets() -> List[str]:
    """Returns the list of python download links from the latest github release, or a specific python-build-standalone release if specified."""
    url = GITHUB_API_URL
    if PYVM_PBS_RELEASE == "latest":
        url += "/latest"

    try:
        release_data = _fetch(url, "json")
    except urllib.error.URLError as e:
        # raise
        raise Exception(
            f"Unable to fetch python-build-standalone release data (from {url})."
        ) from e

    if PYVM_PBS_RELEASE != "latest":
        release_data = [
            release
            for release in release_data
            if release["tag_name"] == PYVM_PBS_RELEASE
        ]
        if not release_data:
            raise Exception(
                f"Unable to find python-build-standalone release {PYVM_PBS_RELEASE}."
            )
        release_data = release_data[0]

    return [asset["browser_download_url"] for asset in release_data["assets"]]  # type: ignore


def _list_pythons() -> Dict[str, str]:
    """Returns available python versions for your machine and their download links."""
    system, machine = platform.system(), platform.machine()
    download_link_suffix = MACHINE_SUFFIX[system][machine]
    # linux suffixes are nested under glibc or musl builds
    if system == "Linux":
        # fallback to musl if libc version is not found
        libc_version = platform.libc_ver()[0] or "musl"
        download_link_suffix = download_link_suffix[libc_version]

    python_assets = _get_or_update_index()["assets"]

    available_python_links = [
        link for link in python_assets if link.endswith(download_link_suffix)
    ]

    python_versions: dict[str, str] = {}
    for link in available_python_links:
        match = PYTHON_VERSION_REGEX.search(link)
        if match is None:
            logger.warning(
                f"Could not parse python version from link {link}. Skipping."
            )
            continue
        python_version = match[1]
        python_versions[python_version] = link

    sorted_python_versions = {
        version: python_versions[version]
        for version in sorted(
            python_versions,
            # sort by semver
            key=lambda version: [int(k) for k in version.split(".")],
            reverse=True,
        )
    }
    return sorted_python_versions


def _resolve_python_version(requested_version: str):
    pythons = _list_pythons()

    for version, version_download_link in pythons.items():
        if version.startswith(requested_version):
            python_version = version
            download_link = version_download_link
            break
    else:
        raise NotAvailable(f"Python version {requested_version} is not available.")

    return python_version, download_link


def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")
    list_parser = subparsers.add_parser("list", help="List installed python versions")
    install_parser = subparsers.add_parser("install", help="Install a python version")
    install_parser.add_argument(
        "version", nargs="?", help="The version of python to install"
    )
    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Uninstall a python version"
    )
    uninstall_parser.add_argument(
        "version", nargs="?", help="The version of python to install"
    )
    update_parser = subparsers.add_parser(
        "update", help="Update all installed python versions"
    )
    run_parser = subparsers.add_parser("run", help="Run a python version")
    run_parser.add_argument("version", help="The version of python to run")
    run_parser.add_argument(
        "args", nargs=argparse.REMAINDER, help="Arguments to pass to the python binary"
    )
    pipx_parser = subparsers.add_parser("pipx", help="Run pipx")
    pipx_parser.add_argument("version", help="The version of python to run pipx with")
    pipx_parser.add_argument(
        "args", nargs=argparse.REMAINDER, help="Arguments to pass to pipx"
    )

    args = parser.parse_args()

    match args.command:
        case "list":
            list_installed_versions()
        case "install":
            if not args.version:
                list_available_versions()
                exit(1)
            install_version(args.version)
        case "uninstall":
            assert args.version, "Please specify a version to uninstall"
            uninstall_version(args.version)
        case "update":
            update_all_versions()
        case "run":
            bin = ensure_version(args.version)
            os.execl(bin, bin, *args.args)
        case "pipx":
            bin = ensure_version(args.version)
            pipx_zipapp = ensure_pipx()
            os.execl(bin, bin, pipx_zipapp, *args.args)
        case None:
            parser.print_help()
            exit(1)


if __name__ == "__main__":
    main()
