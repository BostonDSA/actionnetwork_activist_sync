"""
This lambda reads an email that was put in S3 by SES. The email must
have a secret header set otherwise this ignores the email. It converts
the CSV attachment from the email into DynamoDB items. The CSV attachment
is of the format that gets exported from ActionKit.
"""

import boto3
import csv
import datetime
import email
import email.policy
import json
import localstack_client.session
import logging
import os
from pythonjsonlogger import jsonlogger
import sys
import uuid
from urllib.parse import unquote_plus

from actionnetwork_activist_sync.state_model import State

logger = logging.getLogger()
json_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
json_handler.setFormatter(formatter)
logger.addHandler(json_handler)
logger.removeHandler(logger.handlers[0])

dynamodb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')

if os.environ.get('ENVIRONMENT') == 'local':
    dynamodb_client = localstack_client.session.Session().client('dynamodb')
    s3_client = localstack_client.session.Session().client('s3')

batch = datetime.date.today().strftime('%Y%U')

def lambda_handler(event, context):
    """
    This handler is meant to be attached to an S3 bucket and triggered
    when objects are placed into that bucket. If the object has an attachment
    and header that matches what we're expecting, then the CSV attachment
    will be ingested into DynamoDB.
    """

    for record in event['Records']:

        # Fetch email from bucket
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        tmpkey = key.replace('/', '')
        download_path = f'/tmp/{uuid.uuid4()}{tmpkey}'
        logger.info(
            'Downloading file from bucket',
            extra={"bucket": bucket, "key": key, "download_path": download_path})
        s3_client.download_file(bucket, key, download_path)

        # Parse email and CSV attachment
        with open(download_path) as email_file:
            msg = email.message_from_file(email_file, policy=email.policy.default)

            if os.environ.get('DSA_KEY') != msg.get('DsaKey'):
                logger.error('DSA Key not found in email header, aborting.')
                return

            try:
                [attach] = [a for a in msg.iter_attachments() if a.get_content_type() == 'application/vnd.ms-excel']
            except(ValueError):
                # No CSV, something is wrong
                sys.exit(0)

            csv_lines = attach.get_content().decode().splitlines()

            count = 0
            for row in csv.DictReader(csv_lines):
                d_row = dict(row)

                if not 'Email' in d_row:
                    # We can't continue processing without an email
                    pass

                state = State(
                    d_row['Email'],
                    batch,
                    raw=json.dumps(d_row),
                    status=State.UNPROCESSED
                )
                state.save()

                count += 1

            logger.info('Finished processing CSV.', extra={'num_rows': count})
