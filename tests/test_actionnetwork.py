# -*- coding: utf-8 -*-
"""Tests for actionnetwork module"""

import unittest

from actionnetwork_activist_sync.actionnetwork import ActionNetwork

@unittest.skip("integration test, for dev only")
class TestActionNetwork(unittest.TestCase):
    """Test the ActionNetwork helper class

    This test interacts with live data so disabled by default.
    Set an email before trying to run.
    """

    def setUp(self):
        self.actionnetwork = ActionNetwork()
        self.email = ''

    def test_get_people_by_email(self):
        """Test searching for someone based on email"""

        people = self.actionnetwork.get_people_by_email(self.email)
        self.assertEqual(people[0].email_addresses[0]['address'], self.email)

    def test_remove_member_by_email(self):
        """Test updating the membership flag

        Don't do this on a real member."""

        updated_people = self.actionnetwork.remove_member_by_email(self.email)
        self.assertEqual(updated_people[0].custom_fields['is_member'], '0')
