"""
This lambda watches item updates on a DynamoDB changes. It only
cares about new items. Those items have the raw data that represents
a single rows of an ActionKit export CSV. These rows get synced
into ActionNetwork via API.
"""

import json
import os

from agate.rows import Row
from keycloak import KeycloakAdmin
from tenacity import Retrying, stop_after_attempt, wait_fixed

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.field_mapper import FieldMapper
from actionnetwork_activist_sync.keycloak import KeycloakService
from actionnetwork_activist_sync.logging import get_logger
from actionnetwork_activist_sync.state_model import State
from actionnetwork_activist_sync.util import get_secret

BATCH_SIZE = 200

def lambda_handler(event, context):
    """
    This handler gets triggered by the step function after the ingester has converted
    CSV rows into DynamoDB items. It handles creating new and updating existing users.
    """

    logger = get_logger('lambda_processor')

    dry_run = os.environ.get('DRY_RUN') != '0'

    api_key = get_secret('ACTIONNETWORK_API_KEY')

    actionnetwork = get_actionnetwork(api_key)
    keycloak = get_keycloak()

    logger.info(
        'Starting to process DynamoDB items', extra={
            'dry_run': dry_run
        })

    new = event['new_members'] if 'new_members' in event else 0
    updated = event['updated_members'] if 'updated_members' in event else 0

    unprocessed = State.query(
        hash_key=event['batch'],
        filter_condition=State.status == State.UNPROCESSED,
        limit=BATCH_SIZE
    )

    for item in unprocessed:

        item.status = State.PROCESSING
        item.save()

        from_csv = json.loads(item.raw)
        row = Row(from_csv.values(), from_csv.keys())
        field_mapper = FieldMapper(row)
        people = actionnetwork.get_people_by_email(item.email)

        if len(people) == 0:
            person = field_mapper.get_actionnetwork_person()

            logger.info('Creating new member', extra={'email': item.email})
            new += 1

            if not dry_run:
                for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
                    with attempt:
                        actionnetwork.create_person(**person)
        else:
            for existing_person in people:
                field_mapper.person_id = existing_person.get_actionnetwork_id()
                updated_person = field_mapper.get_actionnetwork_person()
                field_mapper.overrides = existing_person.get_overrides()

                logger.info('Updating member', extra={
                    'person_id': field_mapper.person_id,
                    'email': item.email
                    })
                updated += 1

                if not dry_run:
                    for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
                        with attempt:
                            actionnetwork.update_person(**updated_person)

        keycloak_user_id = keycloak.get_user_by_email(item.email)

        if keycloak_user_id:
            logger.info('Updating keycloak', extra={
                'keycloak_user_id': keycloak_user_id
            })

            keycloak.update_user(keycloak_user_id)

        else:
            logger.info('Creating new user in keycloak', extra={
                'email': item.email
            })

            keycloak.create_user(item.email)

        item.status = State.PROCESSED
        item.save()

    logger.info('Finished processing batch of records', extra={
        'new': new,
        'update': updated
    })

    remainder = State.count(
        hash_key=event['batch'],
        filter_condition=State.status == State.UNPROCESSED
        )

    result = {
        'new_members': new,
        'updated_members': updated,
        'hasMore': (remainder != 0)
    }

    event.update(result)
    return event

def get_actionnetwork(api_k):
    """Creates an ActionNetwork object.

    This function is a helper for mocking in tests"""

    return ActionNetwork(api_k)

def get_keycloak():
    """
    Gets a KeycloakAdmin object to interact with the Keycloak API
    """

    return KeycloakService(
        KeycloakAdmin(
            server_url="https://auth.bostondsa.org/auth/",
            client_id=os.environ.get('KEYCLOAK_CLIENT_ID'),
            client_secret_key=os.environ.get('KEYCLOAK_CLIENT_SECRET_KEY'),
            realm_name=os.environ.get('KEYCLOAK_REALM'),
            verify=True
        )
    )
