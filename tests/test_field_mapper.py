# -*- coding: utf-8 -*-
"""Test field conversions"""

import unittest

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

        field_mapper = FieldMapper({'Mobile_Phone': raw})
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

        field_mapper = FieldMapper({'Zip': raw})
        actual = field_mapper.get_postal_code()
        self.assertEqual(expected, actual)
