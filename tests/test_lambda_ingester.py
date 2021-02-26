import csv
from email.message import EmailMessage
import io
import os
import unittest
import zipfile

from moto import mock_s3, mock_dynamodb2
import boto3
from lambda_local.context import Context

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'CRITICAL'
os.environ['DSA_KEY'] = 'TESTKEY'

class TestIngester(unittest.TestCase):

    @mock_s3
    def test_email_missing_header(self):
        from lambda_ingester import lambda_handler

        email = EmailMessage()
        email['Subject'] = 'Boat for sale'
        email['From'] = 'spam@example.com'
        email['To'] = 'test@example.com'

        bucket = 'actionnetworkactivistsync'
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket,Key='test.email',Body=email.as_bytes())

        self.assertRaisesRegex(
            ValueError,
            'DSA Key not found',
            lambda_handler,
            self.get_event(bucket),
            Context(5))

    @mock_s3
    def test_email_attachment_wrong_mime(self):
        from lambda_ingester import lambda_handler

        email = EmailMessage()
        email['Subject'] = 'Boat for sale'
        email['From'] = 'spam@example.com'
        email['To'] = 'test@example.com'
        email.add_header('DsaKey', 'TESTKEY')
        email.add_attachment(
            'random text'.encode(), maintype='text', subtype='plain')

        bucket = 'actionnetworkactivistsync'
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket,Key='test.email',Body=email.as_bytes())

        self.assertRaisesRegex(
            ValueError,
            'ZIP',
            lambda_handler,
            self.get_event(bucket),
            Context(5))

    @mock_s3
    @mock_dynamodb2
    def test_csv_gets_added_to_db(self):
        import lambda_ingester
        from actionnetwork_activist_sync.state_model import State

        csv_data = [
            ['Email', 'Firstname', 'Lastname'],
            ['kmarx@marxists.org', 'Karl', 'Marx']
        ]

        fake_zip = self.get_zipped_csv(csv_data)

        email = EmailMessage()
        email['Subject'] = 'ActionNetwork Sync'
        email['From'] = 'sync@example.com'
        email['To'] = 'test@example.com'
        email.add_header('DsaKey', 'TESTKEY')
        email.add_attachment(
            fake_zip.getvalue(), maintype='application', subtype='zip')

        bucket = 'actionnetworkactivistsync'
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket,Key='test.email',Body=email.as_bytes())

        State.create_table(billing_mode='PAY_PER_REQUEST')
        lambda_ingester.lambda_handler(self.get_event(bucket), Context(5))
        try:
            State.get(lambda_ingester.batch, range_key='kmarx@marxists.org')
        except State.DoesNotExist:
            self.fail('Item not found in dynamodb')

    @mock_s3
    @mock_dynamodb2
    def test_missing_email_gets_skipped(self):
        import lambda_ingester
        from actionnetwork_activist_sync.state_model import State

        csv_data = [
            ['Email', 'Firstname', 'Lastname'],
            ['', 'Karl', 'Marx']
        ]

        fake_zip = self.get_zipped_csv(csv_data)

        email = EmailMessage()
        email['Subject'] = 'ActionNetwork Sync'
        email['From'] = 'sync@example.com'
        email['To'] = 'test@example.com'
        email.add_header('DsaKey', 'TESTKEY')
        email.add_attachment(
            fake_zip.getvalue(), maintype='application', subtype='zip', filename='test.zip')

        bucket = 'actionnetworkactivistsync'
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket,Key='test.email',Body=email.as_bytes())

        State.create_table(billing_mode='PAY_PER_REQUEST')
        lambda_ingester.lambda_handler(self.get_event(bucket), Context(5))
        self.assertEqual(0, State.count())
        fake_zip.close()

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

    def get_zipped_csv(self, csv_data):
        fake_csv = io.StringIO()
        csv_f = csv.writer(fake_csv)
        csv_f.writerows(csv_data)

        fake_zip = io.BytesIO()
        z = zipfile.ZipFile(fake_zip, 'w')
        z.writestr('test.csv', fake_csv.getvalue())
        z.close()
        return fake_zip
