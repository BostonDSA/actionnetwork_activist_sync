# -*- coding: utf-8 -*-
"""Interacts with ActionNetwork API

https://actionnetwork.org/docs
"""

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

    def get_person_by_id(self, id):
        """Get a person by the ActionNetwork ID

        Args:
            id (str): ActionNetwork ID

        Returns:
            Person object
        """

        for _ in range(0, 3):
            try:
                response = self.get_person(person_id=id)
            except requests.exceptions.ConnectionError:
                time.sleep(5)
            if response:
                break

        if not response:
            raise Exception('Failed to contact ActionNetwork API to get person')

        return Person(**response)

    def subscribe_person(self, person):
        """

        """



    def get_neighborhood_reports(self):
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
        """

        """

        base = self.resource_to_url('lists')
        url = f'{base}?page={page}'
        resp = requests.get(url, headers=self.headers).json()
        return resp['_embedded']['osdi:lists']

    def is_neighborhood_report(self, report):
        """

        """

        return 'name' in report \
        and report['name'].startswith('Neighborhood -') \
        and report['description'] == 'Report'

    def get_people_from_report(self, report, page=1):
        """

        """

        list_url = report['_links']['self']['href']
        url = f'{list_url}/items?page={page}'
        resp = requests.get(url, headers=self.headers).json()
        return resp['_embedded']['osdi:items']

    def get_all_people_from_report(self, report):
        """

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
