import csv
from email.message import EmailMessage
import io
import logging
import os
import unittest

from moto import mock_s3, mock_secretsmanager, mock_dynamodb2
import boto3
from lambda_local.main import call
from lambda_local.context import Context

from actionnetwork_activist_sync.state_model import State

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['DSA_KEY'] = 'TESTKEY'
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

        self.assertRaisesRegex(
            ValueError,
            'DSA Key not found',
            lambda_ingester.lambda_handler,
            self.get_event(bucket),
            Context(5))

    @mock_s3
    def test_email_attachment_wrong_mime(self):
        email = EmailMessage()
        email['Subject'] = 'Boat for sale'
        email['From'] = 'spam@example.com'
        email['To'] = 'test@example.com'
        email.add_header('DsaKey', 'TESTKEY')
        email.add_attachment(
            'random text'.encode(), maintype='text', subtype='plain')

        bucket = 'actionnetworkactivistsync'
        s3 = boto3.client('s3', region_name='us-east-1')
        lambda_ingester.s3_client = s3
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket,Key='test.email',Body=email.as_bytes())

        self.assertRaisesRegex(
            ValueError,
            'CSV',
            lambda_ingester.lambda_handler,
            self.get_event(bucket),
            Context(5))

    @mock_s3
    def test_csv_gets_added_to_db(self):
        csv_data = [
            ['Email', 'Firstname', 'Lastname'],
            ['kmarx@marxists.org', 'Karl', 'Marx']
        ]

        fake_file = io.StringIO()
        csv_f = csv.writer(fake_file)
        csv_f.writerows(csv_data)

        email = EmailMessage()
        email['Subject'] = 'ActionNetwork Sync'
        email['From'] = 'sync@example.com'
        email['To'] = 'test@example.com'
        email.add_header('DsaKey', 'TESTKEY')
        email.add_attachment(
            fake_file.getvalue().encode(), maintype='text', subtype='csv')

        bucket = 'actionnetworkactivistsync'
        s3 = boto3.client('s3', region_name='us-east-1')
        lambda_ingester.s3_client = s3
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket,Key='test.email',Body=email.as_bytes())

        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        lambda_ingester.dynamodb_client = dynamodb

        State._get_connection().connection._client = dynamodb
        lambda_ingester.State = State

        call(lambda_ingester.lambda_handler, self.get_event(bucket), Context(5))

    def get_event(self, bucket):
        return {
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

