# 'Tainers

'Tainers is a simple replacement for testcontainers-python. 

## What is it?

'Tainers lightly wraps the docker SDK, providing enough functionality to cover 80% of the tc-p use-case. Perfect for making custom containers for integration and end-to-end tests.

## Install

`pip install tainers`

## Usage


### Using in dind

'Tainers respects the `DOCKER_HOST` environment variable, meaning it should just work with docker-in-docker.