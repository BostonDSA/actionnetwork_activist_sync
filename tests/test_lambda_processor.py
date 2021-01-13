import os
import unittest

from moto import mock_dynamodb2, mock_secretsmanager
import boto3
from lambda_local.context import Context

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'CRITICAL'
os.environ['DSA_KEY'] = 'TESTKEY'

class TestProcessor(unittest.TestCase):

    @mock_secretsmanager
    def test_load_key_from_secret(self):
        os.environ['ACTIONNETWORK_API_KEY'] = 'arn:secretid'
        secrets_client = boto3.client('secretsmanager')
        secrets_client.put_secret_value(
            SecretId='arn:secretid',
            SecretString='{"ACTIONNETWORK_API_KEY":"X"}'
        )
        import lambda_processor
        self.assertEqual(lambda_processor.api_key, 'X')