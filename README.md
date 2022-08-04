# 'Tainers

'Tainers is a simple replacement for testcontainers-python. 

## What is it?

'Tainers lightly wraps the docker SDK, providing enough functionality to cover much of the tc-p use-case. Perfect for making custom containers for integration and end-to-end tests.

## Install

`pip install tainers`

## Usage

```py
from tainers import Tainer

import requests

python_server = Tainer("python:3.9")
python_server.with_command(["python", "-m", "http.server"])
python_server.with_port(8000, host=8080)

with python_server as container:
    resp = requests.get(python_server.url(8000))
    print(resp)

> <Response [200]>
```

You can also subclass `Tainer` to make your own specialized containers as code.

### Using in dind

'Tainers respects the `DOCKER_HOST` environment variable, meaning it should just work with docker-in-docker.