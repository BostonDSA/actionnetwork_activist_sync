"""
This lambda watches item updates on a DynamoDB changes. It only
cares about new items. Those items have the raw data that represents
a single rows of an ActionKit export CSV. These rows get synced
into ActionNetwork via API.
"""
import json
import os

from agate.rows import Row
import boto3

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.field_mapper import FieldMapper
from actionnetwork_activist_sync.state_model import State

logger = get_logger('lambda_processor')

dry_run = os.environ.get('DRY_RUN') != '0'
dynamodb_client = boto3.client('dynamodb')
secrets_client = boto3.client('secretsmanager')

api_key = os.environ['ACTIONNETWORK_API_KEY']
if api_key.startswith('arn'):
    secret = secrets_client.get_secret_value(SecretId=api_key)
    secret_dict = json.loads(secret['SecretString'])
    api_key = secret_dict['ACTIONNETWORK_API_KEY']
    logger.debug('Using API key from Secrets Manager')
else:
    logger.debug('Using API key from Env')

if os.environ.get('ENVIRONMENT') == 'local':
    import localstack_client.session
    dynamodb_client = localstack_client.session.Session().client('dynamodb')

def lambda_handler(event, context):
    """
    This handler is meanted to be trigged by changes on a DynamoDB table
    that has ActionKit CSV rows stored as items. It handles creating new and
    updating existing users.
    """

    actionnetwork = get_actionnetwork(api_key)

    logger.info(
        'Starting to process DynamoDB items', extra={
            'num_records': len(event['Records']),
            'dry_run': dry_run
        })

    new = 0
    updated = 0

    for record in event['Records']:
        if record['eventName'] != 'INSERT':
            continue

        email = record['dynamodb']['Keys']['email']['S']
        batch = record['dynamodb']['Keys']['batch']['S']
        item = State.get(batch, email)
        item.status = State.PROCESSING
        item.save()

        from_csv = json.loads(item.raw)
        row = Row(from_csv.values(), from_csv.keys())
        field_mapper = FieldMapper(row)
        people = actionnetwork.get_people_by_email(email)

        if len(people) == 0:
            person = field_mapper.get_actionnetwork_person()
            logger.info('Creating new member', extra={'email': person['email']})
            new += 1
            if not dry_run:
                actionnetwork.create_person(**person)
        else:
            for existing_person in people:
                field_mapper.person_id = existing_person.get_actionnetwork_id()
                updated_person = field_mapper.get_actionnetwork_person()
                field_mapper.overrides = existing_person.get_overrides()

                logger.info('Updating member', extra={'person_id': field_mapper.person_id})
                updated += 1
                if not dry_run:
                    actionnetwork.update_person(**updated_person)

        if not dry_run:
            item.status = State.PROCESSED
            item.save()

    return (new, updated)

def get_actionnetwork(api_k):
    """Creates an ActionNetwork object.

    This function is a helper for mocking in tests"""

    return ActionNetwork(api_k)
