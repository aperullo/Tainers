import os
from unittest.mock import MagicMock, patch

import pytest

from tainers import Tainer


@pytest.fixture
def docker():
    mock_client = MagicMock()
    with patch("tainers.tainer.docker") as mocker:
        mocker.from_env.return_value = mock_client
        yield mock_client


def test_container_propertry(docker: MagicMock):
    tainer = Tainer("image")
    tainer._container_id = "container_id"
    result = tainer._container

    docker.containers.get.assert_called_with("container_id")


# Each tuple is a test case of format
# (func_name, param_name, func_args, expected)
params = [
    ("with_command", "command", (["my", "command"],), ["my", "command"]),
    ("with_volume", "volumes", ("/my/volume",), ["/my/volume"]),
    ("with_env", "environment", ("key", "value"), {"key": "value"}),
    ("with_label", "labels", ({"key": "value"},), {"key": "value"}),
    ("with_port", "ports", (8080, 8080), {8080: 8080}),
]


@pytest.mark.parametrize("func_name, param_name, func_args, expected", params)
def test_with(func_name, param_name, func_args, expected):
    """
    This parametrization generates tests that are the equivalent of the following, but for each the "with_" function:

    def test_with_command():
        tainer = Tainer("image")
        tainer.with_command(["my", "command"])
        assert tainer.command == ["my", "command"]
    """

    tainer = Tainer("image")
    func = getattr(tainer, func_name)
    func(*func_args)

    assert getattr(tainer, param_name) == expected


def test_docker_client():
    with patch("tainers.tainer.docker") as mocker:
        tainer = Tainer("image")
        result = tainer.docker_client

        mocker.from_env.assert_called_with()
        assert result == mocker.from_env()


def test_start():
    with patch("tainers.tainer.Tainer.docker_client") as mocker, patch(
        "tainers.tainer.Tainer.is_ready", return_value=True
    ) as is_ready:

        tainer = Tainer("image")
        tainer.start()

        mocker.containers.run.assert_called_with(
            "image", detach=True, name=None, command=[], environment={}, labels={}, ports={}, volumes=[], **{}
        )


def test_start_hooks():
    with patch("tainers.tainer.Tainer.docker_client") as mocker, patch(
        "tainers.tainer.Tainer.is_ready", return_value=True
    ) as is_ready:

        tainer = Tainer("image")
        tainer.pre_start = MagicMock()
        tainer.post_start = MagicMock()
        tainer.start()

        tainer.pre_start.assert_called()
        tainer.post_start.assert_called()


def test_stop():
    with patch("tainers.tainer.Tainer._container", return_value=MagicMock()):
        tainer = Tainer("image")
        tainer.stop()

        tainer._container.stop.assert_called_with()
        tainer._container.remove.assert_called_with(force=True, v=True)


def test_stop_hooks():
    with patch("tainers.tainer.Tainer._container", return_value=MagicMock()):
        tainer = Tainer("image")
        tainer.pre_stop = MagicMock()
        tainer.post_stop = MagicMock()
        tainer.stop()

        tainer.pre_stop.assert_called()
        tainer.post_stop.assert_called()


def test_context_manager():
    with patch("tainers.tainer.Tainer.start") as mock_start, patch("tainers.tainer.Tainer.stop") as mock_stop:

        with Tainer("image"):
            mock_start.assert_called_with()
        mock_stop.assert_called_with()


def test_host_port_not_started(docker: MagicMock):
    with pytest.raises(RuntimeError, match="Container not started"):
        tainer = Tainer("image")
        tainer.host_port(8080)


def test_host_port_no_ports(docker: MagicMock):
    docker.api.port.return_value = None
    with pytest.raises(ValueError, match="Container port not mapped to host port"):
        tainer = Tainer("image")
        tainer._container_id = "container_id"
        tainer.ports = {8080: 9090}
        host_port = tainer.host_port(8080)


def test_host_port(docker: MagicMock):
    docker.api.port.return_value = [{"HostPort": 9090}]
    tainer = Tainer("image")
    tainer._container_id = "container_id"
    tainer.ports = {8080: 9090}

    host_port = tainer.host_port(8080)

    assert host_port == 9090


def test_host_name_not_set():
    with patch.dict(os.environ, {}, clear=True):
        tainer = Tainer("image")
        result = tainer.host_name()

        assert result == "localhost"


def test_host_name_set():
    with patch.dict(os.environ, {"DOCKER_HOST": "tcp://docker:2000"}, clear=True):
        tainer = Tainer("image")
        result = tainer.host_name()

        assert result == "docker"


def test_url():
    with patch("tainers.tainer.Tainer.host_port", return_value=8080) as mock_host_port, patch(
        "tainers.tainer.Tainer.host_name", return_value="docker"
    ) as mock_host_name:
        tainer = Tainer("image")
        result = tainer.url(8080)

        mock_host_port.assert_called_with(8080)
        mock_host_name.assert_called()
        assert result == "http://docker:8080"
