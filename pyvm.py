#!/bin/bash
# region preamble
""":"
set -euo pipefail

# These values will have to be hard-coded for now until i find a better way to aquire them within this limited bash context
SELF_PY_VERSION=3.12.1
SELF_RELEASE_DATE=20240107

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
tar -xvf "$archive"
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
and symlink versioned executables (ie `python3.12` for python 3.12) into a directory on the PATH.

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
from functools import partial
from pathlib import Path
from typing import Any, Dict, List
import urllib.error
from urllib.request import urlopen


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

GITHUB_API_URL = "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest"
PYTHON_VERSION_REGEX = re.compile(r"cpython-(\d+\.\d+\.\d+)")

WINDOWS = platform.system() == "Windows"
PYVM_HOME = Path(os.environ.get('PYVM_HOME', os.path.join(os.environ['HOME'], '.pyvm')))
PYVM_TMP = PYVM_HOME / 'tmp'
PYVM_BIN = Path(os.environ.get('PYVM_BIN', os.path.join(os.environ['HOME'], '.local/bin')))


class NotAvailable(Exception):
    """Raised when the asked Python version is not available."""


logger = logging.getLogger(__name__)


def _installed_versions():
    for installed_version in PYVM_HOME.glob('3.*/bin'):
        major_minor = installed_version.parent.name
        installed_bin = installed_version / f'python{major_minor}'
        yield major_minor, installed_bin

def list_installed_versions():
    installations_found = False
    for major_minor, _ in _installed_versions():
        msg = f'python{major_minor} is installed'
        if (symlink := PYVM_BIN / f'python{major_minor}').exists():
            msg += f' and symlinked to {symlink.resolve()}'
        logger.info(msg)
        installations_found = True
    if not installations_found:
        logger.info('No python installations installed through pyvm')


def list_available_versions():
    pythons = _list_pythons()
    installed_pythons = [major_minor for major_minor, _ in _installed_versions()]
    logger.info("Available python versions:")
    pythons = [version.split('.') for version in pythons]
    pythons = sorted(pythons, key=lambda version: [int(k) for k in version])
    for version in pythons:
        msg = f"{version[0]}.{version[1]:2} --> {version[0]}.{version[1]}.{version[2]}"
        if f"{version[0]}.{version[1]}" in installed_pythons:
            msg += " (installed)"
        logger.info(msg)


def install_version(version: str):
    version = _normalize_python_version(version)
    python_bin = download_python_build_standalone(version)
    _link_python_binary(python_bin, version)


def _ensure_pyvm_bin_dir():
    Path(PYVM_BIN).mkdir(parents=True, exist_ok=True)
    for bin_dir in os.environ['PATH'].split(os.pathsep):
        if PYVM_BIN.samefile(bin_dir):
            return
    else:
        print(f'Please add {PYVM_BIN} to your PATH')
        print(f'Ex, add the following to your shell profile: export PATH=$PATH:{PYVM_BIN}')


def _link_python_binary(path: str, version: str):
    _ensure_pyvm_bin_dir()
    Path(PYVM_BIN / f'python{version}').symlink_to(path)


def _normalize_python_version(python_version: str) -> str:
    # python_version can be a bare version number like "3.9" or a "binary name" like python3.10
    # we'll convert it to a bare version number
    return re.sub(r"[c]?python", "", python_version)


def download_python_build_standalone(python_version: str):
    """Attempt to download and use an appropriate python build
    from https://github.com/indygreg/python-build-standalone
    and unpack it into the PYVM_HOME directory. 
    Returns the full path to the python binary within that build"""
    python_bin = "python.exe" if WINDOWS else "python3"

    install_dir = PYVM_HOME / python_version
    installed_python = install_dir / "bin" / python_bin

    if installed_python.exists():
        return str(installed_python)

    if install_dir.exists():
        logger.warning(f"A previous attempt to install python {python_version} failed. Retrying.")
        shutil.rmtree(install_dir)

    try:
        full_version, download_link = _resolve_python_version(python_version)
    except NotAvailable as e:
        raise Exception(f"Unable to acquire a standalone python build matching {python_version}.") from e

    with tempfile.TemporaryDirectory() as tempdir:
        archive = Path(tempdir) / f"python-{full_version}.tar.gz"
        download_dir = Path(tempdir) / "download"

        # download the python build gz
        _download(full_version, download_link, archive)

        # unpack the python build
        _unpack(full_version, download_link, archive, download_dir)

        # the python installation we want is nested in the tarball
        # under a directory named 'python'. We move it to the install
        # directory
        extracted_dir = download_dir / "python"
        extracted_dir.rename(install_dir)

    return str(installed_python)


def _download(full_version: str, download_link: str, archive: Path):
    logger.info(f"Downloading python {full_version} build")
    try:
        # python standalone builds are typically ~32MB in size. to avoid
        # ballooning memory usage, we read the file in chunks
        with urlopen(download_link) as response, open(archive, "wb") as file_handle:
            for data in iter(partial(response.read, 32768), b""):
                file_handle.write(data)
    except urllib.error.URLError as e:
        raise Exception(f"Unable to download python {full_version} build.") from e


def _unpack(full_version, download_link, archive: Path, download_dir: Path):
    logger.info(f"Unpacking python {full_version} build")
    # Calculate checksum
    with open(archive, "rb") as python_zip:
        checksum = hashlib.sha256(python_zip.read()).hexdigest()

    # Validate checksum
    checksum_link = download_link + ".sha256"
    expected_checksum = urlopen(checksum_link).read().decode().rstrip("\n")
    if checksum != expected_checksum:
        raise Exception(
            f"Checksum mismatch for python {full_version} build. " f"Expected {expected_checksum}, got {checksum}."
        )

    with tarfile.open(archive, mode="r:gz") as tar:
        tar.extractall(download_dir)


def _get_or_update_index():
    """Get or update the index of available python builds from
    the python-build-standalone repository."""
    index_file = PYVM_HOME / "index.json"
    if index_file.exists():
        index = json.loads(index_file.read_text())
        # update index after 30 days
        fetched = datetime.datetime.fromtimestamp(index["fetched"])
        if datetime.datetime.now() - fetched > datetime.timedelta(days=30):
            index = {}
    else:
        index = {}
    if not index:
        releases = _get_latest_python_releases()
        index = {"fetched": datetime.datetime.now().timestamp(), "releases": releases}
        # update index
        index_file.write_text(json.dumps(index))
    return index


def _get_latest_python_releases() -> List[str]:
    """Returns the list of python download links from the latest github release."""
    try:
        with urlopen(GITHUB_API_URL) as response:
            release_data = json.load(response)

    except urllib.error.URLError as e:
        # raise
        raise Exception(f"Unable to fetch python-build-standalone release data (from {GITHUB_API_URL}).") from e

    return [asset["browser_download_url"] for asset in release_data["assets"]]


def _list_pythons() -> Dict[str, str]:
    """Returns available python versions for your machine and their download links."""
    system, machine = platform.system(), platform.machine()
    download_link_suffix = MACHINE_SUFFIX[system][machine]
    # linux suffixes are nested under glibc or musl builds
    if system == "Linux":
        # fallback to musl if libc version is not found
        libc_version = platform.libc_ver()[0] or "musl"
        download_link_suffix = download_link_suffix[libc_version]

    python_releases = _get_or_update_index()["releases"]

    available_python_links = [link for link in python_releases if link.endswith(download_link_suffix)]

    python_versions: dict[str, str] = {}
    for link in available_python_links:
        match = PYTHON_VERSION_REGEX.search(link)
        if match is None:
            logger.warning(f"Could not parse python version from link {link}. Skipping.")
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
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(message)s')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest='command')
    list_parser = subparsers.add_parser('list', help='List installed python versions')
    install_parser = subparsers.add_parser('install', help='Install a python version')
    install_parser.add_argument('version', nargs='?', help='The version of python to install')
    args = parser.parse_args()

    match args.command:
        case 'list':
            list_installed_versions()
        case 'install':
            if not args.version:
                list_available_versions()
                exit(1)
            install_version(args.version)
        case None:
            parser.print_help()
            exit(1)

if __name__ == "__main__":
    main()
