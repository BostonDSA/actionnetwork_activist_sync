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
import os
import sys
import uuid
from urllib.parse import unquote_plus

from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.state_model import State

logger = get_logger('lambda_ingester')

dynamodb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

if os.environ.get('ENVIRONMENT') == 'local':
    import localstack_client.session
    dynamodb_client = localstack_client.session.Session().client('dynamodb')
    s3_client = localstack_client.session.Session().client('s3')

dsa_key = os.environ['DSA_KEY']
if dsa_key.startswith('arn'):
    secret = secrets_client.get_secret_value(SecretId=dsa_key)
    secret_dict = json.loads(secret['SecretString'])
    dsa_key = secret_dict['DSA_KEY']
    logger.debug('Using DSA key from Secrets Manager')
else:
    logger.debug('Using DSA key from Env')

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

            if dsa_key != msg.get('DsaKey'):
                raise ValueError('DSA Key not found in email header, aborting.')

            try:
                attach = next(msg.iter_attachments())
            except(StopIteration):
                raise StopIteration('No attachements')

            if not attach.get_content_type() == 'text/csv':
                logger.error(
                    'Attachment is not CSV',
                    extra={'content_type': attach.get_content_type()})
                raise ValueError('Attachment is not CSV')

            # decode()
            csv_lines = attach.get_content().splitlines()

            count = 0
            for row in csv.DictReader(csv_lines):
                d_row = dict(row)

                if not 'Email' in d_row or not d_row['Email']:
                    # We can't continue processing without an email
                    continue

                state = State(
                    d_row['Email'],
                    batch,
                    raw=json.dumps(d_row),
                    status=State.UNPROCESSED
                )
                state.save()

                count += 1

            logger.info('Finished processing CSV.', extra={'num_rows': count})
