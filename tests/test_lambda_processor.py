import os
import importlib
import json
import unittest
from unittest.mock import Mock

from moto import mock_dynamodb2, mock_secretsmanager
import boto3
from lambda_local.context import Context

from actionnetwork_activist_sync.osdi import Person

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'CRITICAL'
os.environ['DRY_RUN'] = '1'
os.environ['ACTIONNETWORK_API_KEY'] = 'X'

class TestProcessor(unittest.TestCase):

    @mock_secretsmanager
    def test_load_key_from_secret(self):
        os.environ['ACTIONNETWORK_API_KEY'] = 'arn:secretid'
        secrets_client = boto3.client('secretsmanager')
        secrets_client.put_secret_value(
            SecretId='arn:secretid',
            SecretString='{"ACTIONNETWORK_API_KEY":"X"}'
        )
        import lambda_processor
        self.assertEqual(lambda_processor.api_key, 'X')
        del os.environ['ACTIONNETWORK_API_KEY']

    @mock_dynamodb2
    def test_create_new_member(self):
        import lambda_processor
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        # needed to for different env var
        importlib.reload(lambda_processor)

        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state(State)

        event = {
            'batch': '202101',
            'ingested_rows': 1
        }

        mock_an = Mock(ActionNetwork)
        mock_an.get_people_by_email = Mock(return_value=[])
        lambda_processor.get_actionnetwork = lambda a: mock_an

        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertEqual(result['new_members'], 1)
        self.assertEqual(result['updated_members'], 0)
        self.assertFalse(result['hasMore'])

    @mock_dynamodb2
    def test_update_existing_member(self):
        import lambda_processor
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        # needed to for different env var
        importlib.reload(lambda_processor)

        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state(State)

        event = {
            'batch': '202101',
            'ingested_rows': 1
        }

        karl =  self.get_karl_person()

        mock_an = Mock(ActionNetwork)
        mock_an.get_people_by_email = Mock(return_value=[karl])
        lambda_processor.get_actionnetwork = lambda a: mock_an

        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertEqual(result['new_members'], 0)
        self.assertEqual(result['updated_members'], 1)
        self.assertFalse(result['hasMore'])

    @mock_dynamodb2
    def test_has_more(self):
        import lambda_processor
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        # needed to for different env var
        importlib.reload(lambda_processor)

        lambda_processor.batch_size = 1

        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state(State)
        self.create_friedrich_state(State)

        event = {
            'batch': '202101',
            'ingested_rows': 2
        }

        karl = self.get_karl_person()

        mock_an = Mock(ActionNetwork)
        mock_an.get_people_by_email = Mock(return_value=[karl])
        lambda_processor.get_actionnetwork = lambda a: mock_an

        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertTrue(result['hasMore'])

    @mock_dynamodb2
    def test_counts_go_up(self):
        import lambda_processor
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        # needed to for different env var
        importlib.reload(lambda_processor)

        lambda_processor.batch_size = 1

        State.create_table(billing_mode='PAY_PER_REQUEST')
        self.create_karl_state(State)
        self.create_friedrich_state(State)

        event = {
            'batch': '202101',
            'ingested_rows': 2
        }

        mock_an = Mock(ActionNetwork)

        mock_an.get_people_by_email = Mock(return_value=[self.get_karl_person()])
        lambda_processor.get_actionnetwork = lambda a: mock_an
        result = lambda_processor.lambda_handler(event, Context(5))
        self.assertEqual(result['updated_members'], 1)
        self.assertTrue(result['hasMore'])

        mock_an.get_people_by_email = Mock(return_value=[self.get_friedrich_person()])
        result2 = lambda_processor.lambda_handler(result, Context(5))

        self.assertEqual(result2['updated_members'], 2)
        self.assertFalse(result2['hasMore'])

    def create_karl_state(self, State):
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

    def create_friedrich_state(self, State):
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
