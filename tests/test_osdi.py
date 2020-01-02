# -*- coding: utf-8 -*-
"""Tests OSDI objects"""

import json
import pathlib
import unittest

from actionnetwork_activist_sync.osdi import Person

class TestPerson(unittest.TestCase):
    """Tests the Person class"""

    def test_load_json(self):
        """Test the JSON deserializer"""

        with open(pathlib.Path(__file__).parent / 'data' / 'person.json') as fh:
            person = json.load(fh, object_hook=Person.load_json)
            self.assertEqual('Jane', person.given_name)

    def test_get_actionnetwork_id(self):
        """Test that we can get the AN ID back"""

        with open(pathlib.Path(__file__).parent / 'data' / 'person.json') as fh:
            person = json.load(fh, object_hook=Person.load_json)
            self.assertEqual('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', person.get_actionnetwork_id())

    def test_get_overrides(self):
        """Test that we can get override fields"""

        with open(pathlib.Path(__file__).parent / 'data' / 'person.json') as fh:
            person = json.load(fh, object_hook=Person.load_json)
            self.assertDictEqual({'Phone': '6175555555'}, person.get_overrides())
