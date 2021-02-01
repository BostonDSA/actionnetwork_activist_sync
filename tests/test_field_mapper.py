# -*- coding: utf-8 -*-
"""Test field conversions"""

from datetime import datetime
from decimal import Decimal
import unittest

from agate import Row
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

        field_mapper = FieldMapper(Row([raw], ['Mobile_Phone']))
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

        field_mapper = FieldMapper(Row([raw], ['Zip']))
        actual = field_mapper.get_postal_code()
        self.assertEqual(expected, actual)

    def test_overrides_basic_field(self):
        field_mapper = FieldMapper(Row(['Test'], ['given_name']))
        field_mapper.overrides = {'given_name': 'NewName'}
        person = field_mapper.get_actionnetwork_person()
        self.assertEqual('NewName', person['given_name'])

    def test_overrides_custom_field(self):
        field_mapper = FieldMapper(Row(['6175555555'], ['Mobile_Phone']))
        field_mapper.overrides = {'Phone': '6176666666'}
        person = field_mapper.get_actionnetwork_person()
        self.assertEqual('6176666666', person['custom_fields']['Phone'])

    @data(
        ('Address_Line_2', 'Apt 123', 'Address Line 2', 'Apt 123'),
        ('AK_ID', Decimal(1), 'AK_ID', '1'),
        ('Join_Date', datetime(2020, 1, 9), 'Join Date', '2020-01-09 00:00:00')
    )
    @unpack
    def test_get_custom_fields(self, key, value, expected_key, expected_value):
        field_mapper = FieldMapper(Row([value], [key]))
        custom_fields = field_mapper.get_custom_fields()
        self.assertEqual(custom_fields[expected_key], expected_value)
