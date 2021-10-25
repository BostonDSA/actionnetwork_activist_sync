# -*- coding: utf-8 -*-
"""Interacts with ActionNetwork API

https://actionnetwork.org/docs
"""

import time
import requests

from pyactionnetwork import ActionNetworkApi
from tenacity import Retrying, stop_after_attempt, wait_fixed

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
            for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
                with attempt:
                    url = "{0}people/{1}".format(self.base_url, person.get_actionnetwork_id())
                    payload = {
                        'email_addresses': [{
                            'address': email
                        }],
                        'custom_fields': {'is_member': 'False'}
                    }
                    response = requests.put(url, json=payload, headers=self.headers).json()

            updated_people.append(Person(**response))
        return updated_people

    def get_people_by_email(self, email):
        """Search for people by email

        Args:
            email (str): email address to update

        Returns:
            list of Person objects with updated data
        """

        for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
            with attempt:
                response = self.get_person(search_string=email)

        return [Person(**p) for p in response['_embedded']['osdi:people']]
