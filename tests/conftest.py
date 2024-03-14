from pathlib import Path
import os
import sys
import pickle

import pytest
from testcontainers.core.docker_client import DockerClient
from testcontainers.compose import DockerCompose
from docker.models.containers import Container

ROOT = Path(__file__).parent.parent

sys.path.append(str(ROOT))
import pyvm

@pytest.fixture(scope="session")
def compose() -> dict[str, Container]: # type: ignore
    " Spin up docker compose containers are return a dictionary of containers by service name"
    with DockerCompose(ROOT, build=True) as compose:
        dc = DockerClient().client.containers
        compose_containers = {}
        for container in compose.get_containers():
            compose_containers[container.Service] = dc.get(container.ID)
        yield compose_containers # type: ignore


@pytest.fixture()
def fakefs(tmp_path, mocker) -> tuple[Path, Path, Path]:
    "Mock out PYVM_HOME and PYVM_BIN to temporary folders and return Path objects for them"
    PYVM_HOME = tmp_path / ".pyvm"
    PYVM_HOME.mkdir()
    mocker.patch("pyvm.PYVM_HOME", PYVM_HOME)
    PYVM_BIN = PYVM_HOME / "bin"
    PYVM_BIN.mkdir()
    mocker.patch("pyvm.PYVM_BIN", PYVM_BIN)
    return PYVM_HOME, PYVM_BIN, tmp_path


@pytest.fixture(scope="session")
def mock_github_cache():
    cache = ROOT / ".github_cache"
    if cache.exists():
        with open(cache, "rb") as f:
            return pickle.load(f)
    else:
        return {}


@pytest.fixture()
def mock_fetch(mocker, mock_github_cache):
    "Mock out github API requests"
    
    orig_fetch = pyvm._fetch

    def mocked_fetch(url, type):
        "Fake urlopen that returns cached data if available, otherwise fetches from github"
        if url in mock_github_cache:
            return mock_github_cache[url]
        else:
            res = orig_fetch(url, type)
            mock_github_cache[url] = res
            with open(ROOT / ".github_cache", "wb") as f:
                pickle.dump(mock_github_cache, f)
            return res
    mocker.patch("pyvm._fetch", mocked_fetch)


if os.getenv("VSCODE_DEBUGGER"):
    # set up hooks for VSCode debugger to break on exceptions
    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value

def pytest_addoption(parser: pytest.Parser, pluginmanager):
    """
    Adds configuration option to enable end-to-end tests
    """
    del pluginmanager  # not needed in this context

    parser.addoption(
        "--end-to-end",
        action="store_const",
        default=False,
        const=True,
        dest="run_end_to_end",
        help="Run end-to-end tests (disabled by default)",
    )
    parser.addoption(
        "--no-end-to-end",
        action="store_const",
        const=False,
        dest="run_end_to_end",
        help="Do not run end-to-end tests (default)",
    )


def pytest_configure(config: pytest.Config):
    """
    Register marker for end-to-end tests
    """
    config.addinivalue_line(
        "markers",
        "end_to_end: mark test to run after unit tests "
        "and (quick) integration tests are complete",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item):
    """
    Checks whether tests should be skipped based on markers and command-line flags,
    and environment variables
    """
    if os.getenv("VSCODE_DEBUGGER"):
        return

    if item.get_closest_marker("end_to_end"):
        if item.config.getoption("run_end_to_end") in (None, True):
            return
        pytest.skip("End-to-end tests skipped")