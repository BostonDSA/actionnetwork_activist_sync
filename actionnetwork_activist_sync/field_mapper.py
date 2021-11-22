# -*- coding: utf-8 -*-
"""Logic to convert people data from ActionKit to ActionNetwork"""

from datetime import datetime, date
from decimal import Decimal

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
        if self.exported_person.get('Billing_Address_Line_1'):
            address.append(self.exported_person.get('Billing_Address_Line_1'))

        person = {
            'email': self.exported_person.get('Email'),
            'given_name': self.exported_person.get('first_name', default=''),
            'family_name': self.exported_person.get('last_name', default=''),
            'address': address,
            'city': self.exported_person.get('Billing_City', default=''),
            'state': self.exported_person.get('Billing_State', default=''),
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

        # prefer mobile
        phone = self.exported_person.get('Mobile_Phone')

        # fallback to home
        if not phone:
            phone = self.exported_person.get('Home_Phone')

        # clean phone data
        if phone:
            phone = phone.replace('-', '')
            phone = phone.replace(' ', '')
            multi_phone = phone.split(',')
            phone = multi_phone[0]

        return phone

    def get_postal_code(self):
        """Normalizes postal code data"""

        postal_code = self.exported_person.get('Billing_Zip', default='')
        if postal_code and len(postal_code) < 5 and postal_code.isnumeric():
            postal_code = f'{postal_code:0>5}'

        return postal_code

    def get_is_member(self):
        """Calculates membership status"""

        is_member = True

        xdate = self.exported_person.get('Xdate')
        if isinstance(xdate, date):
            now = datetime.now().date()
            delta = now - xdate

            if delta.days > 60:
                is_member = False

        if self.exported_person.get('membership_status') == "expired":
            is_member = False

        return is_member

    def get_custom_fields(self):
        """Formats custom fields"""

        custom_fields = {
            'Address Line 2': self.exported_person.get('Billing_Address_Line_2'),
            'AK_ID': self.exported_person.get('AK_ID'),
            'BDSA Xdate': self.exported_person.get('Xdate'),
            'Do Not Call': self.exported_person.get('Do_Not_Call'),
            # This is deprecated
            #'DSA_ID': self.exported_person.get('DSA_ID'),
            'Join Date': self.exported_person.get('Join_Date'),
            'Mail Preference': self.exported_person.get('Mail_preference'),
            'Middle Name': self.exported_person.get('middle_name'),
            'Phone': self.get_phone(),
            'is_member': self.is_member,
            'membership_type': self.exported_person.get('membership_type'),
            'membership_status': self.exported_person.get('membership_status'),
            'monthly_dues_status': self.exported_person.get('monthly_dues_status'),
            'union_member': self.exported_person.get('union_member'),
            'union_name': self.exported_person.get('union_name'),
            'union_local': self.exported_person.get('union_local'),
            'student_yes_no': self.exported_person.get('student_yes_no'),
            'student_school_name': self.exported_person.get('student_school_name'),
            'YDSA Chapter': self.exported_person.get('YDSA Chapter')
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