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
json_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
json_handler.setFormatter(formatter)
logger.addHandler(json_handler)
logger.removeHandler(logger.handlers[0])

actionnetwork = ActionNetwork()

dry_run = os.getenv('DRY_RUN', '1') == '1'

dynamodb_client = boto3.client('dynamodb')
if os.environ['ENVIRONMENT'] == 'local':
    import localstack_client.session
    dynamodb_client = localstack_client.session.Session().client('dynamodb')

def lambda_handler(event, context):
    """
    This handler is meanted to be trigged by changes on a DynamoDB table
    that has ActionKit CSV rows stored as items. It handles creating new and
    updating existing users.
    """

    for record in event['Records']:
        if record['eventName'] != 'INSERT':
            continue

        email = record['dynamodb']['Keys']['email']['S']
        batch = record['dynamodb']['Keys']['batch']['S']
        items = State.query(email, State.batch == batch)
        for item in items:
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
