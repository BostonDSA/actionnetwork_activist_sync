"""
This lambda reads an email that was put in S3 by SES. The email must
have a secret header set otherwise this ignores the email. It converts
the CSV attachment from the email into DynamoDB items. The CSV attachment
is of the format that gets exported from ActionKit.
"""

import csv
import datetime
import email
import email.policy
import io
import json
import os
import uuid
from urllib.parse import unquote_plus
import zipfile

import boto3

from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.state_model import State

logger = get_logger('lambda_ingester')

if os.environ.get('ENVIRONMENT') == 'local':
    import localstack_client.session
    session = localstack_client.session.Session()
else:
    session = boto3.session.Session()

dynamodb_client = session.client('dynamodb')
s3_client = session.client('s3')
secrets_client = session.client('secretsmanager')

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

    count = 0

    # Fetch email from bucket
    bucket = event['bucketName']
    key = unquote_plus(event['key'])
    tmpkey = key.replace('/', '')
    download_path = f'/tmp/{uuid.uuid4()}{tmpkey}'
    logger.info(
        'Downloading file from bucket',
        extra={"bucket": bucket, "key": key, "download_path": download_path})
    s3_client.download_file(bucket, key, download_path)

    with open(download_path) as email_file:
        # The full email gets deposited in the S3 bucket
        msg = email.message_from_file(email_file, policy=email.policy.default)

        if dsa_key != msg.get('DsaKey'):
            raise ValueError('DSA Key not found in email header, aborting.')

        # ActionKit mails the report as an attached ZIP file
        attach = next(msg.iter_attachments())

        if not attach.get_content_type() in ['application/zip', 'application/x-zip-compressed']:
            logger.error(
                'Attachment is not ZIP',
                extra={'content_type': attach.get_content_type()})
            raise ValueError('Attachment is not ZIP')

        zip_data = io.BytesIO(attach.get_content())

        with zipfile.ZipFile(zip_data) as zip:
            names = zip.namelist()
            if len(names) != 1:
                raise ValueError('ZIP archive has wrong number of files')

            if not names[0].endswith('.csv'):
                raise ValueError('ZIP archive is missing CSV file')

            csv_lines = io.StringIO(zip.read(names[0]).decode('utf-8'))


        for row in csv.DictReader(csv_lines):
            d_row = dict(row)

            if 'Email' not in d_row or not d_row['Email']:
                # We can't continue processing without an email
                continue

            if not 'skip_db' in event:
                state = State(
                    batch,
                    d_row['Email'],
                    raw=json.dumps(d_row),
                    status=State.UNPROCESSED
                )
                state.save()

            count += 1

        logger.info('Finished processing CSV.', extra={'num_rows': count})

    return {
        'batch': batch,
        'ingested_rows': count
    }