"""
This lambda compares new batches to previous batches to detect
which records are missing from the new one. These indicate that
a membership has lapsed.
"""

import datetime
import json
import os

from agate.rows import Row
import boto3

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.field_mapper import FieldMapper
from actionnetwork_activist_sync.state_model import State

logger = get_logger('lambda_lapsed')

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

cur_batch = datetime.date.today().strftime('%Y%U')
last_week = datetime.date.today() - datetime.timedelta(weeks=1)
prev_batch = last_week.strftime('%Y%U')

def lambda_handler(event, context):
    """
    Detect changes
    Flip is_member
    """

    removed = 0
    cur_count = State.count(hash_key=cur_batch)
    prev_count = State.count(hash_key=prev_batch)

    cur_items = State.query(hash_key=cur_batch)
    logger.info(
        'Loaded current items.',
        extra={'cur_batch': cur_batch, 'num_items': cur_count})

    prev_items = State.query(hash_key=prev_batch)
    logger.info(
        'Loaded previous items.',
        extra={'prev_batch': prev_batch, 'num_items': prev_count})

    cur_emails = [c.email for c in cur_items]
    prev_emails = [p.email for p in prev_items]

    if cur_count == 0 or len(cur_emails) == 0:
        raise RuntimeError('No current batch, something is probably wrong. Aborting')

    logger.info(
        'Checking previous email list against current',
        extra={
            'cur_email_count': len(cur_emails),
            'prev_email_count': len(prev_emails)
        }
    )

    action_network = get_actionnetwork(api_key)

    for prev_email in prev_emails:
        if prev_email not in cur_emails:
            logger.info(
                'Turing is_member off for lapsed member',
                extra={'email': prev_email}
            )
            if not dry_run:
                action_network.remove_member_by_email(prev_email)
            removed += 1

    return (removed, cur_count, prev_count)

def get_actionnetwork(api_key):
    return ActionNetwork(api_key)
