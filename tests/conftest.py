from pathlib import Path
from typing import Callable

import pytest
from testcontainers.core.docker_client import DockerClient
from testcontainers.compose import DockerCompose
from docker.models.containers import Container

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def compose() -> Callable[[str], Container]: # type: ignore
    with DockerCompose(ROOT, build=True) as compose:
        def get_container(service: str):
            container_info = compose.get_container(service)
            container: Container = DockerClient().client.containers.get(container_info.ID) # type: ignore
            return container
        yield get_container # type: ignore