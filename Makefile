# Developer

shell:
	-pipenv shell

local-init:
	docker-compose up -d
	terraform -chdir=terraform-dev init
	terraform -chdir=terraform-dev apply -auto-approve -var='secrets={"ACTIONNETWORK_API_KEY":"${ACTIONNETWORK_API_KEY}"}'

# Developer Step Function

local-exec-stepfn: local-upload-sample
	awslocal stepfunctions start-execution --state-machine-arn arn:aws:states:us-east-1:000000000000:stateMachine:actionnetwork_activist_sync --input '{"bucketName": "actionnetworkactivistsync.bostondsa.net", "key": "sample.eml"}'

# Developer Ingest

local-ingest: local-upload-sample local-ingest-run

local-upload-sample:
	awslocal s3 cp samples/sample.eml s3://actionnetworkactivistsync.bostondsa.net/sample.eml

local-ingest-run:
	pipenv run python-lambda-local -f lambda_handler lambda_ingester.py samples/lambda_ingester_event.json

# Developer Processor

local-processor:
	pipenv run python-lambda-local -f lambda_handler lambda_processor.py samples/lambda_processor_event.json

# Developer Lapsed Cron

local-lapsed:
	pipenv run python-lambda-local -f lambda_handler lambda_lapsed.py samples/lambda_lapsed_event.json

# Developer Neighborhood Cron

local-hood:
	pipenv run python-lambda-local -t 60 -f lambda_handler lambda_neighborhoods.py samples/lambda_neighborhoods_event.json

# Tests

test:
	pipenv run green

# Releasing

build:
	docker build --tag ansync-build -o dist .

deploy:
	terraform -chdir=terraform-prod apply
