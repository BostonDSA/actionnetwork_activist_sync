# -*- coding: utf-8 -*-
"""

"""

import os
import types
import requests

import agate
import agateexcel
from pyactionnetwork import ActionNetworkApi

action_network = ActionNetworkApi(os.environ['ACTIONNETWORK_API_KEY'])

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

def row_to_person(row, person_id=None):
    """
    Converts an ActionKit export row to ActionNetworkApi person arguments.
    """

    person = {
        'email': row['Email'],
        'given_name': row['first_name'],
        'family_name': row['last_name'],
        # TODO: should addr2 be in the offical part or in custom?
        'address': [row['Address_Line_1'], row['Address_Line_2']],
        'city': row['City'],
        'country': row['Country'],
        'postal_code': row['Zip'],
        'custom_fields': {
            # 'DSA_ID': row['DSA_ID'],
            'AK_ID': row['AK_ID'],
            'BDSA Xdate': row['Xdate'],
            'Do Not Call': row['Do_Not_Call'],
            'Join Date': row['Join_Date'],
            'Mail Preference': row['Mail_preference'],
            'Middle Name': row['middle_name'],
            # TODO: what's correct logic for these?
            'Phone': row['Mobile_Phone'],
            # 'Memb_status': row['Memb_status'],
            # 'membership_type': row['membership_type'],
            # 'monthly_status': row['monthly_status']
        }
    }

    if person_id:
        person["person_id"] = person_id

    return person

def get_person_id_from_response(response):
    """

    """
    person_id = None
    if response['_embedded']['osdi:people']:
        person = response['_embedded']['osdi:people'].pop()
        person_id = [i[len('action_network:'):] for i in person['identifiers'] if i.startswith('action_network')].pop()
    return person_id

def lambda_handler(event, context):
    """
    The 'main' function that gets invoked by AWS Lambda.

    Performs three main tasks:

    - Deactivate people who were on the old list, but not the new list
    - Update people who are on both lists
    - Create people who were not on the old list, but are on the new list
    """

    # TODO: come up with some system for keeping track of this
    previous = agate.Table.from_xlsx('older.xlsx')
    current = agate.Table.from_xlsx('newer.xlsx')

    # Filter out rows without emails
    previous_with_email = previous.where(lambda row: row['Email'] is not None)
    current_with_email = current.where(lambda row: row['Email'] is not None)

    # Find people who were in the list last time, but no longer are.
    in_previous_not_in_current = previous_with_email.select(['Email']) \
        .join(current_with_email, 'Email', 'Email', columns=['Email']) \
        .where(lambda row: row['Email2'] is None)

    # Take those people off the email lists
    # TODO: implement a membership flag
    for row in in_previous_not_in_current.rows[:2]:
        unsubscribe(row['Email'])

    for row in current_with_email.rows:
        get_person_response = action_network.get_person(search_string=row['Email'])
        if len(get_person_response['_embedded']['osdi:people']) == 0:
            person = row_to_person(row)
            action_network.create_person(**person)

        else:
            person = row_to_person(row, person_id)
            person_id = get_person_id_from_response(get_person_response)
            action_network.update_person(**person)

    return {
        'statusCode': 200,
        'body': 'Sync Complete'
    }

if __name__ == '__main__':
    event = {}
    context = types.SimpleNamespace()
    lambda_handler(event, context)
