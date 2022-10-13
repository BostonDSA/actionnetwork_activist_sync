import boto3
import json
import os

def get_aws_session():
    if os.environ.get('ENVIRONMENT') == 'local':
        import localstack_client.session
        session = localstack_client.session.Session()
    else:
        session = boto3.session.Session()
    return session

def get_secret(name):
    secret = os.environ.get(name)

    if not secret:
        secret_id = os.environ.get('AWS_SECRET_ARN')
        if not secret_id:
            raise ValueError('Secrets cannot be loaded from AWS SecretManager because AWS_SECRET_ARN is not set')

        session = get_aws_session()
        secrets_client = session.client('secretsmanager')
        secret_value = secrets_client.get_secret_value(SecretId=secret_id)
        secret_dict = json.loads(secret_value['SecretString'])

        if name not in secret_dict:
            raise ValueError('Secret not found in AWS SecretManager')

        secret = secret_dict[name]
    return secret

