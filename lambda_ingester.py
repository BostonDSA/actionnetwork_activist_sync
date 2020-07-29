import boto3
import csv
import localstack_client.session
import email
import email.policy
import json
import os
import sys
import uuid
from urllib.parse import unquote_plus

s3_client = boto3.client('s3')
if os.environ['ENVIRONMENT'] == 'local':
    s3_client = localstack_client.session.Session().client('s3')

def lambda_handler(event, context):
    for record in event['Records']:

        # Fetch email from bucket
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        tmpkey = key.replace('/', '')
        download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)
        print('bucket: {} key: {} download_path: {}'.format(bucket, key, download_path))
        s3_client.download_file(bucket, key, download_path)

        # Parse email and CSV attachment
        with open(download_path) as email_file:
            msg = email.message_from_file(email_file, policy=email.policy.default)

            if os.environ['DSA_KEY'] != msg.get('DsaKey'):
                print('DSA Key not found in email header, aborting.')
                return

            try:
                [attach] = [a for a in msg.iter_attachments() if a.get_content_type() == 'application/vnd.ms-excel']
            except(ValueError):
                # No CSV, something is wrong
                sys.exit(0)

            csv_lines = attach.get_content().decode().splitlines()
            for row in csv.DictReader(csv_lines):
                print(json.dumps(dict(row)))
