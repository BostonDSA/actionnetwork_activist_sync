"""
This lambda compares new batches to previous batches to detect
which records are missing from the new one. These indicate that
a membership has lapsed.
"""

import json
import os
from os.path import exists

import boto3

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.logging import get_logger

logger = get_logger('lambda_neighborhoods')

dry_run = os.environ.get('DRY_RUN') != '0'
secrets_client = boto3.client('secretsmanager')

api_key = os.environ['ACTIONNETWORK_API_KEY']
if api_key.startswith('arn'):
    secret = secrets_client.get_secret_value(SecretId=api_key)
    secret_dict = json.loads(secret['SecretString'])
    api_key = secret_dict['ACTIONNETWORK_API_KEY']
    logger.debug('Using API key from Secrets Manager.')
else:
    logger.debug('Using API key from Env.')

neighborhood_map = os.environ['NEIGHBORHOOD_MAP']
if neighborhood_map.startswith('arn'):
    secret = secrets_client.get_secret_value(SecretId=api_key)
    secret_dict = json.loads(secret['SecretString'])
    hood_map = json.loads(secret_dict['NEIGHBORHOOD_MAP'])
elif exists(neighborhood_map):
    with open(neighborhood_map) as file:
        hood_map = json.load(file)
    logger.debug('Using neighborhood map from file.')

def lambda_handler(event, context):
    """
    This lambda is intended to get triggered on a schedule via CloudWatch.
    """

    action_network = get_actionnetwork(api_key)
    reports = action_network.get_neighborhood_reports()

    logger.info(
    'Found neighborhood reports.',
    extra={
        'count': len(reports),
        'dry_run': dry_run
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
                'Missing API key for neighborhood.',
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
            hood_an_person = hood_an.get_person(person_id=person['action_network:person_id'])
            if not 'error' in hood_an_person:
                logger.debug(
                    'Skipping person already subscribed.',
                    extra={
                        'emails': [email['address'] for email in action_network_person['email_addresses']]
                    })
                existing += 1
            else:
                action_network_person = action_network.get_person(person_id=person['action_network:person_id'])
                if not dry_run:
                    hood_an.subscribe_person(action_network_person)
                new += 1
                logger.info(
                    'New person subscribed to neighborhood.',
                        extra={
                            'emails': [email['address'] for email in action_network_person['email_addresses']],
                            'report': report['name']
                        })


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

    return (total_existing, total_new)

def get_actionnetwork(api_k):
    """Creates an ActionNetwork object.

    This function is a helper for mocking in tests"""

    return ActionNetwork(api_k)
