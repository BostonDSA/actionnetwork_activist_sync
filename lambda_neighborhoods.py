"""
This lambda compares new batches to previous batches to detect
which records are missing from the new one. These indicate that
a membership has lapsed.
"""

import os

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.util import get_secret

def lambda_handler(event, context):
    """
    This lambda is intended to get triggered on a schedule via CloudWatch.
    """

    logger = get_logger('lambda_neighborhoods')

    dry_run = os.environ.get('DRY_RUN') != '0'

    api_key = get_secret('ACTIONNETWORK_API_KEY')
    hood_map = get_secret('NEIGHBORHOOD_MAP')

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
                        'emails': [email['address'] for email in hood_an_person['email_addresses']]
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
