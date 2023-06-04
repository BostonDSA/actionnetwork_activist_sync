import os
import unittest
from unittest.mock import Mock

from lambda_local.context import Context

from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.osdi import Person
import lambda_neighborhoods

os.environ['ENVIRONMENT'] = 'TEST'
os.environ['LOG_LEVEL'] = 'CRITICAL'
os.environ['DRY_RUN'] = '0'

class TestNeighborhoods(unittest.TestCase):

    def test_no_reports(self):
        mock_an = Mock(ActionNetwork)
        mock_an.get_neighborhood_reports.return_value = []
        lambda_neighborhoods.get_actionnetwork = lambda a: mock_an

        ret = lambda_neighborhoods.lambda_handler({}, Context(5))
        self.assertEqual((0,0), ret)

    def test_missing_api_key(self):
        os.environ['NEIGHBORHOOD_MAP'] = '{}'

        mock_an = Mock(ActionNetwork)
        mock_an.get_neighborhood_reports.return_value = [{'name': 'Neighborhood - Missing'}]
        lambda_neighborhoods.get_actionnetwork = lambda a: mock_an

        ret = lambda_neighborhoods.lambda_handler({}, Context(5))
        self.assertEqual((0,0), ret)

    def test_report_has_no_new_people(self):
        os.environ['NEIGHBORHOOD_MAP'] = '{"Neighborhood - Missing": "XXX"}'

        mock_an = Mock(ActionNetwork)
        mock_an.get_neighborhood_reports.return_value = [{'name': 'Neighborhood - Missing'}]
        mock_an.get_all_people_from_report.return_value = []

        mock_hood_an = Mock(ActionNetwork)

        lambda_neighborhoods.get_actionnetwork = Mock()
        lambda_neighborhoods.get_actionnetwork.side_effect = [mock_an, mock_hood_an]

        ret = lambda_neighborhoods.lambda_handler({}, Context(5))
        self.assertEqual((0,0), ret)

    def test_report_has_existing_person(self):
        os.environ['NEIGHBORHOOD_MAP'] = '{"Neighborhood - Missing": "XXX"}'

        mock_an = Mock(ActionNetwork)
        mock_an.get_neighborhood_reports.return_value = [{'name': 'Neighborhood - Missing'}]
        mock_an.get_all_people_from_report.return_value = [{
            'action_network:person_id': 1,
            'given_name': 'Karl',
            'family_name': 'Marx',
            'email_addresses': [{
                'primary': True,
                'address': 'kmarx@bostondsa.org',
                'status': 'subscribed'
            }]
        }]

        mock_hood_an = Mock(ActionNetwork)
        mock_hood_an.get_person.return_value = {
            'given_name': 'Karl',
            'family_name': 'Marx',
            'email_addresses': [{
                'primary': True,
                'address': 'kmarx@bostondsa.org',
                'status': 'subscribed'
            }],
        }

        lambda_neighborhoods.get_actionnetwork = Mock()
        lambda_neighborhoods.get_actionnetwork.side_effect = [mock_an, mock_hood_an]

        ret = lambda_neighborhoods.lambda_handler({}, Context(5))
        self.assertEqual((1,0), ret)

    def test_report_has_new_person(self):
        os.environ['NEIGHBORHOOD_MAP'] = '{"Neighborhood - Missing": "XXX"}'
        os.environ['DRY_RUN'] = '0'

        person = {
            'action_network:person_id': 1,
            'given_name': 'Karl',
            'family_name': 'Marx',
            'email_addresses': [{
                'primary': True,
                'address': 'kmarx@bostondsa.org',
                'status': 'subscribed'
            }]
        }

        mock_an = Mock(ActionNetwork)
        mock_an.get_neighborhood_reports.return_value = [{'name': 'Neighborhood - Missing'}]
        mock_an.get_all_people_from_report.return_value = [person]
        mock_an.get_person.return_value = person

        mock_hood_an = Mock(ActionNetwork)
        mock_hood_an.get_person.return_value = {'error': "Couldn't find User with uuid = 000"}

        lambda_neighborhoods.get_actionnetwork = Mock()
        lambda_neighborhoods.get_actionnetwork.side_effect = [mock_an, mock_hood_an]

        ret = lambda_neighborhoods.lambda_handler({}, Context(5))
        mock_an.get_person.assert_called_once_with(person_id=1)
        mock_hood_an.subscribe_person.assert_called_once_with(person)
        self.assertEqual((0,1), ret)
