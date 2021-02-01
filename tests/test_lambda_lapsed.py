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
os.environ['DSA_KEY'] = 'TESTKEY'

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

        cur_karl = State(
            lambda_lapsed.cur_batch,
            'kmarx@marxists.org',
            raw=j_karl,
            status=State.PROCESSED
        )
        cur_karl.save()

        prev_karl = State(
            lambda_lapsed.prev_batch,
            'kmarx@marxists.org',
            raw=j_karl,
            status=State.PROCESSED
        )
        prev_karl.save()

        mock_an = Mock(ActionNetwork)
        lambda_lapsed.get_actionnetwork = lambda a: mock_an

        (rem, cur, prev) = lambda_lapsed.lambda_handler({}, Context(5))

        self.assertEqual(rem, 0)
        self.assertEqual(cur, 1)
        self.assertEqual(prev, 1)

    @mock_dynamodb2
    def test_in_both_but_unprocessed_errors(self):
        import lambda_lapsed
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        State.create_table(billing_mode='PAY_PER_REQUEST')

        j_karl = json.dumps({
                'Email': 'kmarx@marxists.org',
                'firstname': 'Karl',
                'lastname': 'Marx'
        })

        cur_karl = State(
            lambda_lapsed.cur_batch,
            'kmarx@marxists.org',
            raw=j_karl,
            status=State.UNPROCESSED
        )
        cur_karl.save()

        prev_karl = State(
            lambda_lapsed.prev_batch,
            'kmarx@marxists.org',
            raw=j_karl,
            status=State.PROCESSED
        )
        prev_karl.save()

        mock_an = Mock(ActionNetwork)
        lambda_lapsed.get_actionnetwork = lambda a: mock_an

        with self.assertRaises(RuntimeError):
            lambda_lapsed.lambda_handler({}, Context(5))

    @mock_dynamodb2
    def test_in_cur_but_not_in_prev_is_noop(self):
        import lambda_lapsed
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        importlib.reload(lambda_lapsed)
        lambda_lapsed.get_actionnetwork = lambda a: None

        State.create_table(billing_mode='PAY_PER_REQUEST')

        j_karl = json.dumps({
                'Email': 'kmarx@marxists.org',
                'firstname': 'Karl',
                'lastname': 'Marx'
        })

        cur_karl = State(
            lambda_lapsed.cur_batch,
            'kmarx@marxists.org',
            raw=j_karl,
            status=State.PROCESSED
        )
        cur_karl.save()

        mock_an = Mock(ActionNetwork)
        lambda_lapsed.get_actionnetwork = lambda a: mock_an

        (rem, cur, prev) = lambda_lapsed.lambda_handler({}, Context(5))

        self.assertEqual(rem, 0)
        self.assertEqual(cur, 1)
        self.assertEqual(prev, 0)

    @mock_dynamodb2
    def test_not_in_cur_but_in_prev_gets_removed(self):
        import lambda_lapsed
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        # this lets us make sure the mock gets called
        os.environ['DRY_RUN'] = '0'
        importlib.reload(lambda_lapsed)

        State.create_table(billing_mode='PAY_PER_REQUEST')

        j_fried = json.dumps({
                'Email': 'fengles@marxists.org',
                'firstname': 'Friedrich',
                'lastname': 'Engels'
        })

        j_karl = json.dumps({
                'Email': 'kmarx@marxists.org',
                'firstname': 'Karl',
                'lastname': 'Marx'
        })

        cur_fried = State(
            lambda_lapsed.cur_batch,
            'fengles@marxists.org',
            raw=j_fried,
            status=State.PROCESSED
        )
        cur_fried.save()

        prev_karl = State(
            lambda_lapsed.prev_batch,
            'kmarx@marxists.org',
            raw=j_karl,
            status=State.PROCESSED
        )
        prev_karl.save()

        mock_an = Mock(ActionNetwork)
        mock_an.remove_member_by_email = Mock()
        lambda_lapsed.get_actionnetwork = lambda a: mock_an

        (rem, cur, prev) = lambda_lapsed.lambda_handler({}, Context(5))

        mock_an.remove_member_by_email.assert_called_once_with(
            'kmarx@marxists.org'
        )
        self.assertEqual(rem, 1)
        self.assertEqual(cur, 1)
        self.assertEqual(prev, 1)

        del os.environ['DRY_RUN']

    @mock_dynamodb2
    def test_empty_cur_errors(self):
        import lambda_lapsed
        from actionnetwork_activist_sync.actionnetwork import ActionNetwork
        from actionnetwork_activist_sync.state_model import State

        importlib.reload(lambda_lapsed)

        State.create_table(billing_mode='PAY_PER_REQUEST')

        mock_an = Mock(ActionNetwork)
        lambda_lapsed.get_actionnetwork = lambda a: mock_an

        with self.assertRaises(RuntimeError):
            lambda_lapsed.lambda_handler({}, Context(5))
