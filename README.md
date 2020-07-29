# Overview

This code provides automation around syncing the lists from the ActionKit export from national to ActionNetwork. It includes both the logic to sync the data as well as to manage the infrastructure.

# Development

## Prerequesites

### Pipenv

[Pipenv Installation Instructions](https://pipenv-fork.readthedocs.io/en/latest/install.html). The majority of the code is written in Python. Pipenv handles managing the dependencies.

### Terraform

Terraform is distributed as a binary that you [download](https://www.terraform.io/downloads.html) and put on your path. Terraform sets up the infrastructure (both dev and production).

### Docker

Search out documentation for how to install this on your particular operating system.

## Getting Started

* `pipenv install --dev` will pull down and install the Python depencies.
* `pipenv shell` will switch your current shell to the virtual environment.
* `docker-compose up -d` will start a virtual AWS inside of a docker container.
* There are two terraform directories for the two different environments [terraform-prod](terraform-prod/) and [terraform-dev](terraform-dev/). To get started with the development (after localstack is running), enter the terraform-dev directory and run `terraform apply`
* See the [Makefile](Makefile/) for some common tasks.
