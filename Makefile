# Developer Ingest
local-ingest: local-init-ingest local-upload-sample local-ingest-run

local-init-ingest:
	-pipenv shell
	docker-compose up -d
	terraform -chdir=terraform-dev init
	terraform -chdir=terraform-dev apply -auto-approve

local-upload-sample:
	awslocal s3 cp sample.email s3://actionnetworkactivistsync.bostondsa.net/sample.email

local-ingest-run:
	pipenv run python-lambda-local -f lambda_handler lambda_ingester.py lambda_ingester_event.json

# Developer Processor
local-processor:
	pipenv run python-lambda-local -f lambda_handler lambda_processor.py lambda_processor_event.json

# Tests
test:
	pipenv run python3 -m unittest

# Releasing

build:
	docker build --tag ansync-build -o dist .

deploy:
	terraform -chdir=terraform-prod apply
