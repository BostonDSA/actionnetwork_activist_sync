# -*- coding: utf-8 -*-
"""Test field conversions"""

from datetime import datetime
from decimal import Decimal
import unittest

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

        field_mapper = FieldMapper(Row([raw], ['billing_zip']))
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
        ('billing_address_line_2', 'Apt 123', 'Address Line 2', 'Apt 123')
    )
    @unpack
    def test_get_custom_fields(self, key, value, expected_key, expected_value):
        field_mapper = FieldMapper(Row([value], [key]))
        custom_fields = field_mapper.get_custom_fields()
        self.assertEqual(custom_fields[expected_key], expected_value)

    @data(
        ('2020-01-01', 'member', False),
        ('2030-01-01', 'member', True),
        ('2030-01-01', 'expired', False),
    )
    @unpack
    def test_get_is_member(self, xdate, membership_status, expected):
        table = Table.from_object([{'xdate': xdate, 'membership_status': membership_status}])
        field_mapper = FieldMapper(table.rows[0])
        self.assertEqual(field_mapper.get_is_member(), expected)