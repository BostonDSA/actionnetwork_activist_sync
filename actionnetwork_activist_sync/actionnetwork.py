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

    def get_person_by_id(self, person_id):
        """Get a person by the ActionNetwork ID

        Args:
            id (str): ActionNetwork ID

        Returns:
            Person object
        """

        for _ in range(0, 3):
            try:
                response = self.get_person(person_id=person_id)
            except requests.exceptions.ConnectionError:
                time.sleep(5)
            if response:
                break

        if not response:
            raise Exception('Failed to contact ActionNetwork API to get person')

        return Person(**response)

    def subscribe_person(self, person):
        """Subscribe a person to ActionNetwork.

        The email_addresses property determines what is getting subscribed
        an the status. See https://actionnetwork.org/docs/v2/people for the format
        of this field.

        Args:
          person (Person): An OSDI Person

        Returns:
          HTTP Response
        """

        url = "{0}people/".format(self.base_url)
        payload = {'person': {'email_addresses': person.email_addresses}}
        resp = requests.post(url, json=payload, headers=self.headers)
        return resp

    def get_neighborhood_reports(self):
        """Returns all reports based on the naming convetion defined
        in is_neighborhood_report.

        Reference: https://actionnetwork.org/docs/v2/lists

        Returns:
          list of reports.
        """

        page = 1
        reports = []

        while True:
            batch = self.get_reports(page)
            if not batch:
                break
            reports.extend(batch)
            page += 1

        return list(filter(self.is_neighborhood_report, reports))

    def get_reports(self, page=1):
        """Used for the Lists endpoing.

        See: https://actionnetwork.org/docs/v2/lists

        Args:
          page (int): For pagination

        Returns:
          list of OSDI List
        """

        base = self.resource_to_url('lists')
        url = f'{base}?page={page}'
        resp = requests.get(url, headers=self.headers).json()
        return resp['_embedded']['osdi:lists']

    def is_neighborhood_report(self, report):
        """Filter for getting reports based on a naming convention.

        Args:
          report (dict): Report to check

        Returns:
          bool
        """

        return 'name' in report and 'description' in report \
        and report['name'].startswith('Neighborhood -') \
        and report['description'] == 'Report'

    def get_people_from_report(self, report, page=1):
        """Fetchs OSDI Items (people) from an OSDI List (report).

        See: https://actionnetwork.org/docs/v2/items

        Args:
          report (dict): Report from lists endpoint
          page (int): For pagination

        Returns:
          list of OSDI items
        """

        list_url = report['_links']['self']['href']
        url = f'{list_url}/items?page={page}'
        resp = requests.get(url, headers=self.headers).json()
        return resp['_embedded']['osdi:items']

    def get_all_people_from_report(self, report):
        """Handles pagination for fetching all people from a report.

        Args:
          report (dict): Report from lists endpoint

        Returns:
          list of People
        """

        page = 1
        people = []

        while True:
            batch = self.get_people_from_report(report, page)
            if not batch:
                break
            people.extend(batch)
            page += 1

        return people
