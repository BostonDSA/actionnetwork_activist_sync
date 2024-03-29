# -*- coding: utf-8 -*-
"""Test field conversions"""

from datetime import datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from agate import Row, Table
from ddt import ddt, data, unpack

from actionnetwork_activist_sync.field_mapper import FieldMapper

@ddt
class TestFieldMapper(unittest.TestCase):
    """Tests FieldMapper"""

    @data(
        ('5555555555', '5555555555'), # already minimal
        ('555-555-5555', '5555555555'), # with dashes
        ('5555555555 ', '5555555555'), # with spaces
        ('5555555555, 666-666-6666', '5555555555') # multi
    )
    @unpack
    def test_get_phone(self, raw, expected):
        """Test known phone formats"""

        field_mapper = FieldMapper(Row([raw], ['mobile_phone']))
        actual = field_mapper.get_phone()
        self.assertEqual(expected, actual)

    @data(
        ('2467', '02467'),
        ('02150', '02150'),
        ('02134-1000', '02134-1000')
    )
    @unpack
    def test_get_postal_code(self, raw, expected):
        """Test known zip formats"""

        field_mapper = FieldMapper(Row([raw], ['mailing_zip']))
        actual = field_mapper.get_postal_code()
        self.assertEqual(expected, actual)

    def test_overrides_basic_field(self):
        field_mapper = FieldMapper(Row(['Test'], ['given_name']))
        field_mapper.overrides = {'given_name': 'NewName'}
        person = field_mapper.get_actionnetwork_person()
        self.assertEqual('NewName', person['given_name'])

    def test_overrides_custom_field(self):
        field_mapper = FieldMapper(Row(['6175555555'], ['mobile_phone']))
        field_mapper.overrides = {'Phone': '6176666666'}
        person = field_mapper.get_actionnetwork_person()
        self.assertEqual('6176666666', person['custom_fields']['Phone'])

    @data(
        ('mailing_address2', 'Apt 123', 'Address Line 2', 'Apt 123')
    )
    @unpack
    def test_get_custom_fields(self, key, value, expected_key, expected_value):
        field_mapper = FieldMapper(Row([value], [key]))
        custom_fields = field_mapper.get_custom_fields()
        self.assertEqual(custom_fields[expected_key], expected_value)

    @data(
        ('M', True),
        ('L', False)
    )
    @unpack
    def test_get_is_member(self, memb_status_letter, expected):
        table = Table.from_object([{'memb_status_letter': memb_status_letter}])
        field_mapper = FieldMapper(table.rows[0])
        self.assertEqual(field_mapper.get_is_member(), expected)


    @data(
        ('Karl', 'Marx', 9999, 'KarlM9999'), # Happy path
        ('', 'Marx', 9999, 'RoseM9999'), # No first name
        ('Karl', '', 9999, 'Karl9999'), # No last name
        ('Karl', 'Marx', 10, 'KarlM0010') # Zero-padded
    )
    @unpack
    def test_generate_username(self, first, last, rand, expected):
        with patch('random.randint') as mock_rand:
            mock_rand.return_value = rand
            field_mapper = FieldMapper(Row([first, last], ['first_name', 'last_name']))
            self.assertEqual(field_mapper.generate_username(), expected)