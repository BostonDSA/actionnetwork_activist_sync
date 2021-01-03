"""
This lambda watches item updates on a DynamoDB changes. It only
cares about new items. Those items have the raw data that represents
a single rows of an ActionKit export CSV. These rows get synced
into ActionNetwork via API.
"""
import json
import logging
import os

from agate.rows import Row
import boto3
from pythonjsonlogger import jsonlogger

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.field_mapper import FieldMapper
from actionnetwork_activist_sync.state_model import State

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', logging.ERROR))
json_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s')
json_handler.setFormatter(formatter)
logger.addHandler(json_handler)
logger.removeHandler(logger.handlers[0])

dry_run = os.environ.get('DRY_RUN') == '1'

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

actionnetwork = ActionNetwork(api_key)

if os.environ.get('ENVIRONMENT') == 'local':
    import localstack_client.session
    dynamodb_client = localstack_client.session.Session().client('dynamodb')

def lambda_handler(event, context):
    """
    This handler is meanted to be trigged by changes on a DynamoDB table
    that has ActionKit CSV rows stored as items. It handles creating new and
    updating existing users.
    """

    logger.info(
        'Starting to process DynamoDB items', extra={
            'num_records': len(event['Records']),
            'dry_run': dry_run
        })

    for record in event['Records']:
        if record['eventName'] != 'INSERT':
            continue

        email = record['dynamodb']['Keys']['email']['S']
        batch = record['dynamodb']['Keys']['batch']['S']
        items = State.query(email, State.batch == batch)
        for item in items:
            item.status = State.PROCESSING
            item.save()

            from_csv = json.loads(item.raw)
            row = Row(from_csv.values(), from_csv.keys())
            field_mapper = FieldMapper(row)
            people = actionnetwork.get_people_by_email(email)

            if len(people) == 0:
                person = field_mapper.get_actionnetwork_person()
                logger.info('Creating new member', extra={'email': person['email']})
                if not dry_run:
                    actionnetwork.create_person(**person)
            else:
                for existing_person in people:
                    field_mapper.person_id = existing_person.get_actionnetwork_id()
                    updated_person = field_mapper.get_actionnetwork_person()
                    field_mapper.overrides = existing_person.get_overrides()

                    logger.info('Updating member', extra={'person_id': field_mapper.person_id})
                    if not dry_run:
                        actionnetwork.update_person(**updated_person)

            if not dry_run:
                item.status = State.PROCESSED
                item.save()