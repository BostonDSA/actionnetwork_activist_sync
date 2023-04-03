# -*- coding: utf-8 -*-
"""
'Main' controller that does the bulk sync
"""

from actionnetwork_activist_sync.actionkit_export import ActionKitExport
from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.debug import PersonCompare
from actionnetwork_activist_sync.field_mapper import FieldMapper

dry_run = False

def sync(api_key):
    """
    The 'main' function that gets bulk script.

    Performs three main tasks:

    - Deactivate people who were on the old list, but not the new list
    - Update people who are on both lists
    - Create people who were not on the old list, but are on the new list
    """

    actionnetwork = ActionNetwork(api_key)

    previous_file = open('older.csv', 'r')
    current_file = open('newer.csv', 'r')

    actionkit_export = ActionKitExport(previous_file, current_file)
    actionkit_export.load()
    actionkit_export.filter_missing_email()

    no_email = 0
    lapsed = 0
    new_member = 0
    existing_member = 0

    for row in actionkit_export.missing_email.rows:
        print('Missing email: {} {}'.format(row['first_name'], row['last_name']))
        no_email += 1

    # People where are no longer in the current spreadsheet, but were
    # in the previous one have had their membership lapse.

    for row in actionkit_export.get_previous_not_in_current().rows:
        print('Toggle membership flag: {}'.format(row['email']))
        lapsed += 1
        if not dry_run:
            actionnetwork.remove_member_by_email(row['email'])

    for row in actionkit_export.current.rows:
        field_mapper = FieldMapper(row)

        people = actionnetwork.get_people_by_email(row['email'])
        if len(people) == 0:
            person = field_mapper.get_actionnetwork_person()
            print('New member: {}'.format(person['email']))
            new_member += 1
            if not dry_run:
                actionnetwork.create_person(**person)
        else:
            for existing_person in people:
                field_mapper.person_id = existing_person.get_actionnetwork_id()
                updated_person = field_mapper.get_actionnetwork_person()
                field_mapper.overrides = existing_person.get_overrides()

                print('Updating person: {}'.format(field_mapper.person_id))
                existing_member += 1
                comp = PersonCompare(existing_person, updated_person)
                comp.print_diff()
                print()
                if not dry_run:
                    actionnetwork.update_person(**updated_person)

    previous_file.close()
    current_file.close()

    return {
        'no_email': no_email,
        'lapsed': lapsed,
        'new_member': new_member,
        'existing_member': existing_member
    }
