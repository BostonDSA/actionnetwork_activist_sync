# -*- coding: utf-8 -*-
"""
'Main' controller that does the sync
"""

from actionnetwork_activist_sync.actionkit_export import ActionKitExport
from actionnetwork_activist_sync.actionnetwork import ActionNetwork
from actionnetwork_activist_sync.debug import PersonCompare
from actionnetwork_activist_sync.field_mapper import FieldMapper

dry_run = False

def sync():
    """
    The 'main' function that gets invoked by AWS Lambda.

    Performs three main tasks:

    - Deactivate people who were on the old list, but not the new list
    - Update people who are on both lists
    - Create people who were not on the old list, but are on the new list
    """

    actionnetwork = ActionNetwork()

    # TODO: come up with some system for keeping track of this
    previous_file = open('older.csv', 'r')
    current_file = open('newer.csv', 'r')

    actionkit_export = ActionKitExport(previous_file, current_file)
    actionkit_export.load()
    actionkit_export.filter_missing_email()

    for row in actionkit_export.missing_email.rows:
        if dry_run:
            print('Missing email: {} {}'.format(row['first_name'], row['last_name']))
        else:
            # TODO: figure out named based matching
            pass

    # People where are no longer in the current spreadsheet, but were
    # in the previous one have had their membership lapse.

    for row in actionkit_export.get_previous_not_in_current().rows:
        if dry_run:
            print('Toggle membership flag: {}'.format(row['Email']))
        else:
            actionnetwork.remove_member_by_email(row['Email'])
            pass

    for row in actionkit_export.current.rows:
        field_mapper = FieldMapper(row)

        people = actionnetwork.get_people_by_email(row['Email'])
        if len(people) == 0:
            person = field_mapper.get_actionnetwork_person()
            if dry_run:
                print('New member: {}'.format(person['email']))
            else:
                actionnetwork.create_person(**person)
        else:
            for existing_person in people:
                field_mapper.person_id = existing_person.get_actionnetwork_id()
                updated_person = field_mapper.get_actionnetwork_person()
                field_mapper.overrides = existing_person.get_overrides()
                if dry_run:
                    print('Updating person: {}'.format(field_mapper.person_id))
                    comp = PersonCompare(existing_person, updated_person)
                    comp.print_diff()
                    print()
                else:
                    actionnetwork.update_person(**updated_person)

    previous_file.close()
    current_file.close()

    return {
        'statusCode': 200,
        'body': 'Sync Complete'
    }
