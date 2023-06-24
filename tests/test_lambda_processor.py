import os
import importlib
import json
import unittest
from unittest.mock import Mock

from moto import mock_dynamodb2
from lambda_local.context import Context

import lambda_processor
from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.keycloak import KeycloakService
from actionnetwork_activist_sync.osdi import Person
from actionnetwork_activist_sync.state_model import State

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'CRITICAL'
os.environ['DRY_RUN'] = '1'
os.environ['ACTIONNETWORK_API_KEY'] = 'X'

@mock_dynamodb2
class TestProcessor(unittest.TestCase):

    def test_create_new_member(self):
        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state()

        mock_an = Mock(ActionNetwork)
        mock_an.get_people_by_email = Mock(return_value=[])
        lambda_processor.get_actionnetwork = lambda a: mock_an

        mock_keycloak = Mock(KeycloakService)
        mock_keycloak.get_user_by_email = Mock(return_value=None)
        lambda_processor.get_keycloak = lambda: mock_keycloak

        event = {
            'batch': '202101',
            'ingested_rows': 1
        }

        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertEqual(result['new_members'], 1)
        self.assertEqual(result['updated_members'], 0)
        self.assertFalse(result['hasMore'])
        mock_keycloak.create_user.assert_called()

        State.delete_table()

    def test_update_existing_member(self):
        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state()

        event = {
            'batch': '202101',
            'ingested_rows': 1
        }

        karl =  self.get_karl_person()

        mock_an = Mock(ActionNetwork)
        mock_an.get_people_by_email = Mock(return_value=[karl])
        lambda_processor.get_actionnetwork = lambda a: mock_an

        mock_keycloak = Mock(KeycloakService)
        mock_keycloak.get_user_by_email = Mock(return_value=1)
        lambda_processor.get_keycloak = lambda: mock_keycloak

        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertEqual(result['new_members'], 0)
        self.assertEqual(result['updated_members'], 1)
        self.assertFalse(result['hasMore'])
        mock_keycloak.update_user.assert_called()

        State.delete_table()

    def test_has_more(self):
        lambda_processor.BATCH_SIZE = 1

        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state()
        self.create_friedrich_state()

        event = {
            'batch': '202101',
            'ingested_rows': 2
        }

        karl = self.get_karl_person()

        mock_an = Mock(ActionNetwork)
        mock_an.get_people_by_email = Mock(return_value=[karl])
        lambda_processor.get_actionnetwork = lambda a: mock_an

        mock_keycloak = Mock(KeycloakService)
        lambda_processor.get_keycloak = lambda: mock_keycloak

        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertTrue(result['hasMore'])

        State.delete_table()

    def test_counts_go_up(self):
        lambda_processor.BATCH_SIZE = 1

        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state()
        self.create_friedrich_state()

        event = {
            'batch': '202101',
            'ingested_rows': 2
        }

        mock_an = Mock(ActionNetwork)
        mock_an.get_people_by_email = Mock(return_value=[self.get_karl_person()])
        lambda_processor.get_actionnetwork = lambda a: mock_an

        mock_keycloak = Mock(KeycloakService)
        lambda_processor.get_keycloak = lambda: mock_keycloak

        mock_an.get_people_by_email = Mock(return_value=[self.get_friedrich_person()])

        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertEqual(result['updated_members'], 1)
        self.assertTrue(result['hasMore'])


        result2 = lambda_processor.lambda_handler(result, Context(5))
        self.assertEqual(result2['updated_members'], 2)
        self.assertFalse(result2['hasMore'])

        State.delete_table()

    def create_karl_state(self):
        state = State(
            '202101',
            'kmarx@marxists.org',
            raw=json.dumps({
                'Email': 'kmarx@marxists.org',
                'firstname': 'Karl',
                'lastname': 'Marx'
            }),
            status=State.UNPROCESSED
        )
        state.save()
        return state

    def create_friedrich_state(self):
        state = State(
            '202101',
            'fengels@marxists.org',
            raw=json.dumps({
                'Email': 'fengles@marxists.org',
                'firstname': 'Friedrich',
                'lastname': 'Engels'
            }),
            status=State.UNPROCESSED
        )
        state.save()
        return state

    def get_karl_person(self):
        return Person(
            given_name='Karl',
            family_name='Marx',
            email_addresses = ['kmarx@marxists.org'])

    def get_friedrich_person(self):
            return Person(
                given_name='Friedrich',
                family_name='Engels',
                email_addresses = ['fengles@marxists.org'])
