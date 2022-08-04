import logging
import os
import time
import urllib.parse
from typing import Dict, List, Optional

import docker
from docker.models.containers import Container

log = logging.getLogger(__name__)


class Tainer:
    """
    A replacement for a testcontainers-python DockerContainer. Tries to simplify the interace, given 'Tainers smaller scope.
    """

    def __init__(self, image: str, name: Optional[str] = None, timeout: int = 60, **kwargs):
        """
        Create a new Tainer.

        Args:
            image (str): The image to use for the container.
            name (Optional[str], optional): The name for the container. Defaults to None.
            timeout (int, optional): the number of times to run is_ready before giving up and killing the container. Defaults to 60.
        """
        self.timeout = timeout
        self._container_id: str = None

        self.image = image
        self.name: Optional[str] = name
        # An empty list will NOT blank the args, so its an ok default. To do that we would have to accidentally pass ['']. The same is not true of entrypoint.
        self.command: List[str] = []
        self.environment: Dict[str, str] = {}
        self.labels: Dict[str, str] = {}
        self.ports: Dict[int, Optional[int]] = {}
        self.volumes: List[str] = []
        self.kwargs = kwargs

    @property
    def _container(self) -> Container:
        """
        Return the underlying container object. This is a property so that it can be fetched every time it is called, so fields like status will be up-to-date.

        Returns:
            Container: the container
        """
        return self.docker_client.containers.get(self._container_id)

    def with_command(self, command: List[str]) -> "Tainer":
        """
        Add a command to the container.

        Args:
            command (List[str]): The command to run as an array of strings seperated on spaces between args (e.g. ["ls", "-l"])

        Returns:
            Tainer: the Tainer object
        """
        self.command = command
        return self

    def with_env(self, key: str, value: str) -> "Tainer":
        """
        Add an environment variable to the container.

        Args:
            key (str): The key of the environment variable.
            value (str): The value for the environment variable.

        Returns:
            Tainer: the Tainer object
        """
        self.environment[key] = value
        return self

    def with_label(self, labels: Dict[str, str]) -> "Tainer":
        """
        Add labels to the container.

        Args:
            labels (Dict[str, str]): The labels to add to the container.

        Returns:
            Tainer: the Tainer object
        """
        self.labels.update(labels)
        return self

    def with_port(self, container: int, host: Optional[int] = None) -> "Tainer":
        """
        Add ports to the container.

        Args:
            container (int): The port on the container.
            host (Optional[int]): The port on the host. If not specified, becomes a random port.

        Returns:
            Tainer: the Tainer object
        """
        self.ports[container] = host
        return self

    def with_volume(self, volume: str) -> "Tainer":
        """
        Add a volume to the container.

        Args:
            volume (str): The volume to add to the container formatted as it would be to the docker command line. Like
                anonymous volume: "/test"
                bind-mount: "/test:/test"
                nameed volume: "test:/test"

        Returns:
            Tainer: the Tainer object
        """
        self.volumes.append(volume)
        return self

    @property
    def docker_client(self) -> docker.DockerClient:
        """
        Return a docker client.

        Returns:
            docker.DockerClient: the docker client
        """
        return docker.from_env()

    def start(self):
        """
        Start the container using the args provided using the "with_" functions
        """
        client = self.docker_client
        try:
            client.images.get(self.image)
        except docker.errors.ImageNotFound:
            log.info("Pulling image {}".format(self.image))

        _container = client.containers.run(
            self.image,
            detach=True,
            name=self.name,
            command=self.command,
            environment=self.environment,
            labels=self.labels,
            ports=self.ports,
            volumes=self.volumes,
            **self.kwargs
        )

        self._container_id = _container.id

        for _ in range(self.timeout):
            if self.is_ready():
                break
            time.sleep(1)

        log.info("Container started as {}", self._container_id)

    def stop(self, force=True, delete_volume=True):
        self._container.stop()
        self._container.remove(force=force, v=delete_volume)

    def __enter__(self) -> "Tainer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def host_port(self, port: int) -> int:
        """
        Return the host port for a given container port. Based on https://github.com/testcontainers/testcontainers-python/blob/master/testcontainers/core/container.py#L104

        Args:
            port (int): The container port

        Returns:
            int: The host port
        """
        if self._container_id is None:
            raise RuntimeError("Container not started")

        bind_ports = self.docker_client.api.port(self._container.id, port)
        if bind_ports is None:
            raise ValueError("Container port not mapped to host port")
        else:
            return bind_ports[0]["HostPort"]

    def url(self, container_port: int) -> str:
        """
        Return the url for the container, respecting DOCKER_HOST variable.

        Args:
            container_port (int): The container port so we can look up the host port to use in the url.

        Returns:
            str: The url
        """
        docker_host = os.getenv("DOCKER_HOST")
        if docker_host:
            host = urllib.parse.urlparse(docker_host).hostname
        else:
            host = "localhost"

        # TODO: create way to specify default port so this can take no args.
        return "http://{}:{}".format(host, self.host_port(container_port))

    def is_ready(self) -> bool:
        """
        Return whether the container is ready. This should be overriden in subclasses to use something like a health endpoint.

        Returns:
            bool: Whether the container is ready
        """
        if self._container_id is None:
            raise RuntimeError("Container not started")

        return self._container.status == "running"
