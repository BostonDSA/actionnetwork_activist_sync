# -*- coding: utf-8 -*-
"""Interacts with ActionNetwork API

https://actionnetwork.org/docs
"""

import os
import time
import requests

from pyactionnetwork import ActionNetworkApi
from actionnetwork_activist_sync.osdi import Person

class ActionNetwork(ActionNetworkApi):
    """Helper class to interact with the ActionNetwork API"""

    def remove_member_by_email(self, email):
        """Update custom field that flags membership (is_member)

        Args:
            email (str): email address to update

        Returns:
            list of Person objects with updated data
        """

        updated_people = []
        people = self.get_people_by_email(email)
        for person in people:
            for _ in range(0, 3):
                try:
                    response = self.update_person(
                        person_id=person.get_actionnetwork_id(),
                        custom_fields={'is_member': 'False'}
                    )
                except requests.exceptions.ConnectionError:
                    time.sleep(5)
                if response:
                    break

            if not response:
                raise Exception('Failed to contact ActionNetwork API for update')
            updated_people.append(Person(**response))
        return updated_people

    def get_people_by_email(self, email):
        """Search for people by email

        Args:
            email (str): email address to update

        Returns:
            list of Person objects with updated data
        """

        for _ in range(0, 3):
            try:
                response = self.get_person(search_string=email)
            except requests.exceptions.ConnectionError:
                time.sleep(5)
            if response:
                break

        if not response:
            raise Exception('Failed to contact ActionNetwork API to get person')

        return [Person(**p) for p in response['_embedded']['osdi:people']]
