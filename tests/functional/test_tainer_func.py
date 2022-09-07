import docker
import pytest
import requests

from tainers import Tainer


@pytest.mark.functional
def test_image():
    with Tainer("nginx:stable") as nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert container.image.tags[0] == "nginx:stable"


@pytest.mark.functional
def test_name():
    with Tainer("nginx:stable", name="myname") as nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert container.name == "myname"


@pytest.mark.functional
def test_command():
    nginx = Tainer("nginx:stable")
    nginx.with_command(["nginx", "-v"])
    with nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert container.attrs["Config"]["Cmd"] == ["nginx", "-v"]


@pytest.mark.functional
def test_env():
    nginx = Tainer("nginx:stable")
    nginx.with_env("MY_VAR", "my_val")
    with nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert "MY_VAR=my_val" in container.attrs["Config"]["Env"]


@pytest.mark.functional
def test_label():
    nginx = Tainer("nginx:stable")
    nginx.with_label({"MY_LABEL": "my_val"})
    with nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert hasattr(container, "labels")
        assert container.labels["MY_LABEL"] == "my_val"


@pytest.mark.functional
def test_port_bind():
    nginx = Tainer("nginx:stable")
    nginx.with_port(80, host=8080)
    with nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert "80/tcp" in container.ports
        assert container.ports["80/tcp"][0]["HostPort"] == "8080"


@pytest.mark.functional
def test_port_expose():
    nginx = Tainer("nginx:stable")
    nginx.with_port(80)
    with nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert "80/tcp" in container.ports
        assert "HostPort" in container.ports["80/tcp"][0]


@pytest.mark.functional
def test_host_port():
    nginx = Tainer("nginx:stable")
    nginx.with_port(80, host=8080)
    with nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert nginx.host_port(80) == "8080"


@pytest.mark.functional
def test_url():
    nginx = Tainer("nginx:stable")
    nginx.with_port(80)
    with nginx:
        client = docker.from_env()
        container = client.containers.get(nginx._container_id)

        assert "80/tcp" in container.ports
        # since the port will be random, we can't just check for a specific port. Instead we verify that port is serving a page
        assert requests.get(nginx.url(80)).status_code == 200


@pytest.mark.functional
def test_volume(tmp_path):
    # This test verifies the volume persists data

    writer = Tainer("bash:5.0", timeout=0)
    print(tmp_path)
    writer.with_volume("{}:/test_volume".format(tmp_path))
    writer.with_command(["touch", "/test_volume/test_file"])  # with_command was verified in an earlier test
    with writer:
        pass

    reader = Tainer("bash:5.0", timeout=0)
    reader.with_volume("{}:/test_volume".format(tmp_path))
    reader.with_command(["test", "-f", "/test_volume/test_file"])  # returns status_code 0 if file exists
    reader.start()

    client = docker.from_env()
    container = client.containers.get(reader._container_id)
    assert (
        container.attrs["State"]["ExitCode"] == 0
    ), "File didn't exist, the test command exited with a non-zero exit code"

    reader.stop()
