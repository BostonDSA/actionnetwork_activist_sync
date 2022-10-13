import json
import importlib
import os
import unittest
from unittest.mock import Mock

from moto import mock_dynamodb2
import boto3
from lambda_local.context import Context

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'CRITICAL'

class TestLapsed(unittest.TestCase):

    @mock_dynamodb2
    def test_in_both_is_noop(self):
        import lambda_lapsed
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        State.create_table(billing_mode='PAY_PER_REQUEST')

        j_karl = json.dumps({
                'Email': 'kmarx@marxists.org',
                'firstname': 'Karl',
                'lastname': 'Marx'
        })

        self.create_karl_state(State, lambda_lapsed.cur_batch, State.PROCESSED)
        self.create_karl_state(State, lambda_lapsed.prev_batch, State.PROCESSED)

        mock_an = Mock(ActionNetwork)
        lambda_lapsed.get_actionnetwork = lambda a: mock_an

        result = lambda_lapsed.lambda_handler({}, Context(5))

        self.assertEqual(result['removed'], 0)
        self.assertEqual(result['cur_count'], 1)
        self.assertEqual(result['prev_count'], 1)

    @mock_dynamodb2
    def test_not_in_cur_but_in_prev_gets_removed(self):
        import lambda_lapsed
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        # this lets us make sure the mock gets called
        os.environ['DRY_RUN'] = '0'
        importlib.reload(lambda_lapsed)

        State.create_table(billing_mode='PAY_PER_REQUEST')

        self.create_friedrich_state(State, lambda_lapsed.cur_batch, State.PROCESSED)
        self.create_karl_state(State, lambda_lapsed.prev_batch, State.PROCESSED)

        mock_an = Mock(ActionNetwork)
        mock_an.remove_member_by_email = Mock()
        lambda_lapsed.get_actionnetwork = lambda a: mock_an

        result = lambda_lapsed.lambda_handler({}, Context(5))

        mock_an.remove_member_by_email.assert_called_once_with(
            'kmarx@marxists.org'
        )
        self.assertEqual(result['removed'], 1)
        self.assertEqual(result['cur_count'], 1)
        self.assertEqual(result['prev_count'], 1)

        del os.environ['DRY_RUN']

    def create_karl_state(self, State, batch, status):
        state = State(
            batch,
            'kmarx@marxists.org',
            raw=json.dumps({
                'Email': 'kmarx@marxists.org',
                'firstname': 'Karl',
                'lastname': 'Marx'
            }),
            status=status
        )
        state.save()
        return state

    def create_friedrich_state(self, State, batch, status):
        state = State(
            batch,
            'fengels@marxists.org',
            raw=json.dumps({
                'Email': 'fengles@marxists.org',
                'firstname': 'Friedrich',
                'lastname': 'Engels'
            }),
            status=status
        )
        state.save()
        return state
