"""
This lambda compares new batches to previous batches to detect
which records are missing from the new one. These indicate that
a membership has lapsed.
"""

import datetime
import json
import os

import boto3

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.state_model import State

logger = get_logger('lambda_lapsed')

dry_run = os.environ.get('DRY_RUN') != '0'

if os.environ.get('ENVIRONMENT') == 'local':
    import localstack_client.session
    session = localstack_client.session.Session()
else:
    session = boto3.session.Session()

dynamodb_client = session.client('dynamodb')
secrets_client = session.client('secretsmanager')
sns_client = session.client('sns')

api_key = os.environ['ACTIONNETWORK_API_KEY']
if api_key.startswith('arn'):
    secret = secrets_client.get_secret_value(SecretId=api_key)
    secret_dict = json.loads(secret['SecretString'])
    api_key = secret_dict['ACTIONNETWORK_API_KEY']
    logger.debug('Using API key from Secrets Manager')
else:
    logger.debug('Using API key from Env')

cur_batch = datetime.date.today().strftime('%Y%U')
last_week = datetime.date.today() - datetime.timedelta(weeks=1)
prev_batch = last_week.strftime('%Y%U')

def lambda_handler(event, context):
    """
    This lambda is intended to get triggered on a schdule via CloudWatch.
    """

    removed = 0
    cur_count = State.count(hash_key=cur_batch)
    prev_count = State.count(hash_key=prev_batch)

    cur_items = State.query(hash_key=cur_batch, filter_condition=State.status == State.PROCESSED)
    logger.info(
        'Loaded current items.',
        extra={'cur_batch': cur_batch, 'num_items': cur_count})

    prev_items = State.query(hash_key=prev_batch, filter_condition=State.status == State.PROCESSED)
    logger.info(
        'Loaded previous items.',
        extra={'prev_batch': prev_batch, 'num_items': prev_count})

    cur_emails = [c.email for c in cur_items]
    prev_emails = [p.email for p in prev_items]

    errMsg = None

    if cur_count == 0 or len(cur_emails) == 0:
        errMsg = 'No current batch, something is probably wrong. Aborting.'
        logger.error(errMsg)

    if prev_count == 0 or len(prev_emails) == 0:
        errMsg = 'No previous batch. If this is not the first week, then something is probably wrong. Aborting.'
        logger.error(errMsg)

    logger.info(
        'Checking previous email list against current',
        extra={
            'cur_email_count': len(cur_emails),
            'prev_email_count': len(prev_emails)
        }
    )

    action_network = get_actionnetwork(api_key)

    if prev_emails and cur_emails:
        for prev_email in prev_emails:
            if prev_email not in cur_emails:
                logger.info(
                    'Turing is_member off for lapsed member',
                    extra={'email': prev_email}
                )
                if not dry_run:
                    action_network.remove_member_by_email(prev_email)
                removed += 1

    result = {
            'removed': removed,
            'cur_count': cur_count,
            'prev_count': prev_count
    }
    logger.info(
        'Finished removing lapsed members.',
        extra=result)

    event.update(result)

    topic = os.environ.get('SLACK_TOPIC_ARN')
    chan = os.environ.get('SLACK_CHANNEL')

    blocks = []
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": ":package: New member data has been synced from national",
            "emoji": True
        }
	})
    if errMsg:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":warning: `Error` {errMsg}"
            }
        })
    blocks.append({
        "type": "divider"
    })
    blocks.append({
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f":balloon: New members: *{event['new_members'] if 'new_members' in event else 'error'}*"
            },
            {
                "type": "mrkdwn",
                "text": f":cry: Expired members: *{removed}*"
            },
            {
                "type": "mrkdwn",
                "text": f":tada: Updated members: *{event['updated_members'] if 'updated_members' in event else 'error'}*"
            }
        ]
    })
    blocks.append({
        "type": "divider"
    })
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "image",
                "image_url": "https://github.com/favicon.ico",
                "alt_text": "GitHub"
            },
            {
                "type": "mrkdwn",
                "text": "<https://github.com/BostonDSA/actionnetwork_activist_sync|BostonDSA/actionnetwork_activist_sync>\nData is synced weekly on Monday"
            }
        ]
    })

    if os.environ.get('SLACK_ENABLED') == '1' and topic and chan:
        sns_client.publish(
            TopicArn=topic,
            Message=json.dumps({
                "channel": chan,
                "text": "New member data has arrived from national",
                "blocks": blocks
            }),
            MessageAttributes={
                'id': {
                    'DataType': 'String',
                    'StringValue': 'postMessage'
                },
                'type': {
                    'DataType': 'String',
                    'StringValue': 'chat'
                }
            }
        )


    return event

def get_actionnetwork(api_k):
    """Creates an ActionNetwork object.

    This function is a helper for mocking in tests"""

    return ActionNetwork(api_k)
