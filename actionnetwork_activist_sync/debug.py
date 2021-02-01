"""
Helpers for debugging
"""

from colored import attr, fg
from dictdiffer import diff

class PersonCompare:
    """
    This compares two Person objects and visually shows what changed
    """

    def __init__(self, existing, updated):
        self.existing = existing
        self.existing.merge_primary_email()
        self.existing.merge_primary_address()
        self.updated = updated

    def print_diff(self):
        """
        Pretty prints difference between two people in columns.

        Added: White | Green
        Removed: Red | White
        Changed: Yellow
        """

        ignore = [
            'identifiers',
            '_links',
            'created_date',
            'modified_date',
            'languages_spoken',
            'email_addresses',
            'postal_addresses',
            'country',
            'person_id'
        ]

        for difference in diff(self.existing.__dict__, self.updated, ignore=ignore):
            if difference[0] == 'add':
                fmt_str = '{}{:>50}{} | {}{:<50}{}'
                left = ''
                left_color = fg('white')
                right = '{!r} {!r}'.format(difference[1], difference[2])
                right_color = fg('green')
            elif difference[0] == 'remove':
                fmt_str = '{}{:>50}{} | {}{:<50}{}'
                left = '{!r} {!r}'.format(difference[1], difference[2])
                left_color = fg('red')
                right = ''
                right_color = fg('white')
            elif difference[0] == 'change':
                fmt_str = '{}{:>50}{}'
                left = '{!r} {!r}'.format(difference[1], difference[2])
                left_color = fg('yellow')
                right = None
                right_color = None
            else:
                raise NotImplementedError

            print(fmt_str.format(
                left_color, left, attr('reset'), right_color, right, attr('reset')))
