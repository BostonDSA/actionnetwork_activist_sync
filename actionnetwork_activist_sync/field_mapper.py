# -*- coding: utf-8 -*-
"""Logic to convert people data from ActionKit to ActionNetwork"""

from typing import Dict

class FieldMapper:
    """Map fields from ActionKit to ActionNetwork

    Args:
        exported_person (Dict): Single person record from ActionKit

    Attributes:
        exported_person (Dict): Single person record from ActionKit
        person_id (int): ActionNetwork ID (optional)
        overrides (dict): fields to override
        is_member (str): "1" true, "0" false (API uses strings)
    """

    def __init__(self, exported_person: Dict):
        self.exported_person = exported_person
        self.person_id = None
        self.overrides = {}
        self.is_member = "1"

    def get_actionnetwork_person(self) -> Dict:
        """Main conversion method"""

        person = {
            'email': self.exported_person.get('Email'),
            'given_name': self.exported_person.get('first_name'),
            'family_name': self.exported_person.get('last_name'),
            'address': [self.exported_person.get('Address_Line_1')],
            'city': self.exported_person.get('City'),
            'country': self.exported_person.get('Country'),
            'postal_code': self.get_postal_code,
            'custom_fields': {
                'Address Line 2': self.exported_person.get('Address_Line_2'),
                'AK_ID': self.exported_person.get('AK_ID'),
                'BDSA Xdate': self.exported_person.get('Xdate'),
                'Do Not Call': self.exported_person.get('Do_Not_Call'),
                'DSA_ID': self.exported_person.get('DSA_ID'),
                'Join Date': self.exported_person.get('Join_Date'),
                'Mail Preference': self.exported_person.get('Mail_preference'),
                'Middle Name': self.exported_person.get('middle_name'),
                'Phone': self.get_phone(),
                'is_member': self.is_member
                # TODO: not currently in AN, but in AK
                # 'Memb_status': self.exported_person.get('Memb_status'),
                # 'membership_type': self.exported_person.get('membership_type'),
                # 'monthly_status': self.exported_person.get('monthly_status')
            }
        }

        if self.person_id:
            person['person_id'] = self.person_id

        for field, value in self.overrides.items():
            if field in person:
                person[field] = value

            if field in person['custom_fields']:
                person['custom_fields'][field] = value

        return person

    def get_phone(self) -> str:
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

    def get_postal_code(self) -> str:
        """Normalizes postal code data"""

        postal_code = self.exported_person.get('Zip')
        if postal_code and len(postal_code) < 5 and postal_code.isnumeric():
            postal_code = f'{postal_code:0>5}'

        return postal_code
