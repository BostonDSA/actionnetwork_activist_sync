# -*- coding: utf-8 -*-
"""Logic to convert people data from ActionKit to ActionNetwork"""

from datetime import datetime
from decimal import Decimal
import random

class FieldMapper:
    """Map fields from ActionKit to ActionNetwork

    Args:
        exported_person (agate.Row): Single person record from ActionKit

    Attributes:
        exported_person (agate.Row): Single person record from ActionKit
        person_id (int): ActionNetwork ID (optional)
        overrides (dict): fields to override
        is_member (str): "True", "False" (API uses strings)
    """

    def __init__(self, exported_person):
        self.exported_person = exported_person
        self.person_id = None
        self.overrides = {}
        self.is_member = self.get_is_member()

    def get_actionnetwork_person(self):
        """Main conversion method"""

        address = []
        if self.exported_person.get('mailing_address1'):
            address.append(self.exported_person.get('mailing_address1'))

        person = {
            'email': self.exported_person.get('email'),
            'given_name': self.exported_person.get('first_name', default=''),
            'family_name': self.exported_person.get('last_name', default=''),
            'address': address,
            'city': self.exported_person.get('mailing_city', default=''),
            'state': self.exported_person.get('mailing_state', default=''),
            'country': 'US', # no country field in export
            'postal_code': self.get_postal_code(),
            'custom_fields': self.get_custom_fields()
        }

        if self.person_id:
            person['person_id'] = self.person_id

        for field, value in self.overrides.items():
            if field in person:
                person[field] = value

            if field in person['custom_fields']:
                person['custom_fields'][field] = value

        return person

    def get_phone(self):
        """Normalizes phone data"""

        # prefer best_phone
        phone = self.exported_person.get('best_phone')

        # fallback to mobile
        if not phone:
            phone = self.exported_person.get('mobile_phone')

        # fallback to home
        if not phone:
            phone = self.exported_person.get('home_phone')

        if not phone:
            phone = self.exported_person.get('work_phone')

        # clean phone data
        if phone:
            phone = phone.replace('-', '')
            phone = phone.replace(' ', '')
            multi_phone = phone.split(',')
            phone = multi_phone[0]

        return phone

    def get_postal_code(self):
        """Normalizes postal code data"""

        postal_code = self.exported_person.get('mailing_zip', default='')
        if postal_code and len(postal_code) < 5 and postal_code.isnumeric():
            postal_code = f'{postal_code:0>5}'

        return postal_code

    def get_is_member(self):
        """Calculates membership status"""

        is_member = False

        memb_status = self.exported_person.get('memb_status_letter')
        if memb_status == 'M':
            is_member = True

        return is_member

    def get_custom_fields(self):
        """Formats custom fields"""

        custom_fields = {
            'Middle Name': self.exported_person.get('middle_name'),
            # Suffix: not used
            'Address Line 2': self.exported_person.get('mailing_address2'),
            # Mailing_Address1,Mailing_Address2,Mailing_City,Mailing_State,Mailing_Zip: not used
            'Mail Preference': self.exported_person.get('mailing_preference'),
            'Do Not Call': self.exported_person.get('do_not_call'),
            'Do Not Text': self.exported_person.get('p2ptext_optout'),

            'monthly_dues_status': self.exported_person.get('monthly_dues_status'),
            'annual_recurring_dues_status': self.exported_person.get('annual_recurring_dues_status'),

            'union_member': self.exported_person.get('union_member'),
            'union_name': self.exported_person.get('union_name'),
            'union_local': self.exported_person.get('union_local'),
            'student_yes_no': self.exported_person.get('student_yes_no'),
            'student_school_name': self.exported_person.get('student_school_name'),
            'YDSA Chapter': self.exported_person.get('ydsa_chapter'),

            'Phone': self.get_phone(),
            'is_member': self.is_member
        }

        # filter None
        custom_fields = {k:v for k,v in custom_fields.items() if v is not None}

        for k,v in custom_fields.items():
            if isinstance(v, Decimal):
                custom_fields[k] = str(v)
            elif isinstance(v, datetime):
                custom_fields[k] = str(v)
            elif isinstance(v, bool):
                custom_fields[k] = 'True' if v else 'False'

        return custom_fields

    def generate_username(self):
        """
        Generates a username of the format:
            FirstNameLastInitialFourRandomNumbers
        Example:
            Karl Marx -> KarlM9999
        """

        # Fall back to Rose as a default first name.
        # Agate default covers case where first_name doesn't exist,
        # but not when it's None or empty.
        first_name = self.exported_person.get('first_name', default='Rose')
        if not first_name:
            first_name = 'Rose'

        last_initial = self.exported_person.get('last_name', default='')[:1]

        # Add some randomness since FirstName LastIntial has collision potential
        rnd = str(random.randint(10, 9999)).zfill(4)

        return f"{first_name}{last_initial}{rnd}"