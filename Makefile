local-ingest:
	pipenv run python-lambda-local -f lambda_handler lambda_ingester.py lambda_ingester_event.json

local-upload-sample:
	awslocal s3 cp sample.email s3://actionnetworkactivistsync.bostondsa.net/sample.email

local-ls-queue:
	awslocal sqs receive-message --queue-url=http://localhost:4576/000000000000/an-sync-ingested