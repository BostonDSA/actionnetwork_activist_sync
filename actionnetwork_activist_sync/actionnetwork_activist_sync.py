# -*- coding: utf-8 -*-
"""

"""

import os
import types
import requests

import agate
import agateexcel
from pyactionnetwork import ActionNetworkApi

from actionkit_export import ActionKitExport
from field_mapper import FieldMapper
from osdi import Person

action_network = ActionNetworkApi(os.environ['ACTIONNETWORK_API_KEY'])
dry_run = True

def unsubscribe(email):
    """
    Finds people based on email address then updates the attached
    email addresses to be unsubscribed.
    """

    get_person_response = action_network.get_person(search_string=email)
    for person in get_person_response['_embedded']['osdi:people']:
        person_url = person['_links']['self']['href']
        email_addresses = person['email_addresses']
        for email_address in email_addresses:
            if email_address['address'] == email:
                email_address['status'] = 'unsubscribed'
        payload = {'email_addresses': email_addresses}
        requests.put(person_url, json=payload, headers=action_network.headers)

def lambda_handler(event, context):
    """
    The 'main' function that gets invoked by AWS Lambda.

    Performs three main tasks:

    - Deactivate people who were on the old list, but not the new list
    - Update people who are on both lists
    - Create people who were not on the old list, but are on the new list
    """

    # TODO: come up with some system for keeping track of this
    previous_file = open('older.xlsx', 'rb')
    current_file = open('newer.xlsx', 'rb')

    actionkit_export = ActionKitExport(previous_file, current_file)
    actionkit_export.load()
    actionkit_export.filter_missing_email()

    # Take those people off the email lists
    # TODO: implement a membership flag
    for row in actionkit_export.missing_email.rows:
        if dry_run:
            print('Unsubscribe: {} {}'.format(row['first_name'], row['last_name']))
        else:
            #unsubscribe(row['Email'])
            pass

    for row in actionkit_export.get_previous_not_in_current().rows:
        field_mapper = FieldMapper(row)

        get_person_response = action_network.get_person(search_string=row['Email'])
        if len(get_person_response['_embedded']['osdi:people']) == 0:
            person = field_mapper.get_actionnetwork_person()
            if dry_run:
                print('New member: {}'.format(person['email']))
            else:
                #action_network.create_person(**person)
                pass

        else:
            for p in get_person_response['_embedded']['osdi:people']:
                existing_person = Person(**p)
                field_mapper.person_id = existing_person.get_actionnetwork_id()
                updated_person = field_mapper.get_actionnetwork_person()
                if dry_run:
                    print('Existing member: {} ({})'.format(updated_person['email'], updated_person['person_id']))
                else:
                    #action_network.update_person(**person)
                    pass

    previous_file.close()
    current_file.close()

    return {
        'statusCode': 200,
        'body': 'Sync Complete'
    }

if __name__ == '__main__':
    event = {}
    context = types.SimpleNamespace()
    lambda_handler(event, context)
