"""
This lambda compares new batches to previous batches to detect
which records are missing from the new one. These indicate that
a membership has lapsed.
"""

import datetime
import json
import os
from pprint import pprint as pp

import boto3

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.state_model import State

logger = get_logger('lambda_neighborhoods')

dry_run = os.environ.get('DRY_RUN') != '0'
secrets_client = boto3.client('secretsmanager')

api_key = os.environ['ACTIONNETWORK_API_KEY']
if api_key.startswith('arn'):
    secret = secrets_client.get_secret_value(SecretId=api_key)
    secret_dict = json.loads(secret['SecretString'])
    api_key = secret_dict['ACTIONNETWORK_API_KEY']
    logger.debug('Using API key from Secrets Manager')
else:
    logger.debug('Using API key from Env')

hood_map = os.environ['NEIGHBORHOOD_MAP']
if hood_map.startswith('arn'):
    raise NotImplementedError
    # secret = secrets_client.get_secret_value(SecretId=api_key)
    # secret_dict = json.loads(secret['SecretString'])
    # logger.debug('Using API key from Secrets Manager')
else:
    hood_map = json.loads(hood_map)
    logger.debug('Using API key from Env')

def lambda_handler(event, context):
    """
    This lambda is intended to get triggered on a schdule via CloudWatch.
    """

    action_network = get_actionnetwork(api_key)
    reports = action_network.get_neighborhood_reports()

    logger.info(
    'Found neighborhood reports',
    extra={
        'count': len(reports)
    })


    total_existing = 0
    total_new = 0

    for report in reports:
        logger.info(
            'Starting report',
            extra={
                'report_name': report['name']
        })

        if not report['name'] in hood_map:
            logger.warning(
                'Missing API key for neighborhood',
                extra={
                    'report_name': report['name']
            })
            continue

        hood_api = hood_map[report['name']]
        hood_an = get_actionnetwork(hood_api)

        people = action_network.get_all_people_from_report(report)

        existing = 0
        new = 0

        for person in people:
            if hood_an.get_person(person['action_network:person_id']):
                existing += 1
            else:
                new += 1
                # add subscription

        logger.info(
        'Completed neighborhood.',
        extra={
            'existing': existing,
            'new': new
        })

        total_existing += existing
        total_new += new

    logger.info(
        'Completed neighbor sync.',
        extra={
            'total_existing': total_existing,
            'total_new': total_new
        })

def get_actionnetwork(api_k):
    """Creates an ActionNetwork object.

    This function is a helper for mocking in tests"""

    return ActionNetwork(api_k)
