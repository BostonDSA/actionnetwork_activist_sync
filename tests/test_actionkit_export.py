# -*- coding: utf-8 -*-
"""Tests for actionkit_export module"""

import pathlib
import unittest

import agate

from actionnetwork_activist_sync.actionkit_export import ActionKitExport

def get_file(filename):
    """Helper to load Excel test data"""
    return open(pathlib.Path(__file__).parent / 'data' / filename, 'r')


class TestActionKitExport(unittest.TestCase):
    """Tests the ActionKitExport class"""

    def test_load_no_file_handles(self):
        """Try to load without files"""
        export = ActionKitExport(None, None)
        with self.assertRaises(TypeError):
            export.load()

    def test_load_valid_files(self):
        """Try to load with test files"""
        prev = get_file('01previous.csv')
        cur = get_file('01current.csv')

        export = ActionKitExport(prev, cur)
        export.load()

        self.assertIsInstance(export.previous, agate.table.Table)
        self.assertIsInstance(export.current, agate.table.Table)

        prev.close()
        cur.close()

    def test_filter_missing_email(self):
        """Load then filter with data that is missing emails

        Previous has two rows, one missing email
        Current has two rows, one missing email
        """
        prev = get_file('02previous.csv')
        cur = get_file('02current.csv')

        export = ActionKitExport(prev, cur)
        export.load()
        export.filter_missing_email()

        self.assertEqual(len(export.missing_email.rows), 1)
        self.assertEqual(len(export.previous.rows), 1)
        self.assertEqual(len(export.current.rows), 1)

        prev.close()
        cur.close()

    def test_get_previous_not_in_current(self):
        """The full happy path"""

        prev = get_file('01previous.csv')
        cur = get_file('01current.csv')

        export = ActionKitExport(prev, cur)
        export.load()
        export.filter_missing_email()
        previous_not_in_current = export.get_previous_not_in_current()

        self.assertEqual(previous_not_in_current.rows[0]['Email'], 'john.doe@example.com')

        prev.close()
        cur.close()
