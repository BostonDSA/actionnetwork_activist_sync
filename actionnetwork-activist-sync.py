import agate
import agateexcel
from pyactionnetwork import ActionNetworkApi
import requests
import os
import types

action_network = ActionNetworkApi(os.environ["ACTIONNETWORK_API_KEY"])

def unsubscribe(email):
    get_person_response = action_network.get_person(search_string=email)
    for person in get_person_response["_embedded"]["osdi:people"]:
        person_url = person["_links"]["self"]["href"]
        email_addresses = person["email_addresses"]
        for email_address in email_addresses:
            if email_address["address"] == email:
                email_address["status"] = "unsubscribed"
        requests.put(person_url, json={"email_addresses": email_addresses}, headers=action_network.headers)

def lambda_handler(event, context):
    # TODO: come up with some system for keeping track of this
    previous = agate.Table.from_xlsx("older.xlsx")
    current = agate.Table.from_xlsx("newer.xlsx")

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

    return {
        'statusCode': 200,
        'body': 'Sync Complete'
    }

if __name__ == "__main__":
    event = {}
    context = types.SimpleNamespace()
    lambda_handler(event, context)
