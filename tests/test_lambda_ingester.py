from email.message import EmailMessage
import logging
import os
import unittest

from moto import mock_s3, mock_secretsmanager, mock_dynamodb2
import boto3
from lambda_local.main import call
from lambda_local.context import Context

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'INFO'
import lambda_ingester

class TestPerson(unittest.TestCase):

    @mock_s3
    def test_email_missing_header(self):
        email = EmailMessage()
        email['Subject'] = 'Boat for sale'
        email['From'] = 'spam@example.com'
        email['To'] = 'test@example.com'

        bucket = 'actionnetworkactivistsync'
        s3 = boto3.client('s3', region_name='us-east-1')
        lambda_ingester.s3_client = s3
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket,Key='test.email',Body=email.as_bytes())

        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {
                            'name': bucket
                        },
                        'object': {
                            'key': 'test.email'
                        }
                    }
                }
            ]
        }

        context = Context(5)

        self.assertRaises(
            ValueError,
            lambda_ingester.lambda_handler,
            event,
            context)