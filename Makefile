start-ingest: init-ingest local-upload-sample

init-ingest:
	-pipenv shell
	docker-compose up -d
	cd terraform-dev && terraform apply -auto-approve && cd ..

local-ingest:
	pipenv run python-lambda-local -f lambda_handler lambda_ingester.py lambda_ingester_event.json

local-processor:
	pipenv run python-lambda-local -f lambda_handler lambda_processor.py lambda_processor_event.json

local-upload-sample:
	awslocal s3 cp sample.email s3://actionnetworkactivistsync.bostondsa.net/sample.email
