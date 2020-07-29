local-ingest:
	pipenv run python-lambda-local -f lambda_handler lambda_ingester.py lambda_ingester_event.json

local-upload-sample:
	awslocal s3 cp sample.email s3://actionnetworkactivistsync.bostondsa.net/sample.email
