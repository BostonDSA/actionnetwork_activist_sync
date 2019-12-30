# -*- coding: utf-8 -*-
"""
Partial implementation of http://opensupporter.github.io/osdi-docs/
as used by ActionNetwork
"""

class Person:
    """
    People are individual users who are stored in the OSDI system’s
    database in some way.

    People have names, email addresses, and other information,
    and they have associated action histories recording the actions
    they’ve taken on the system, such as a list of their signatures
    on various petitions.

    Args:
        given_name (str)The person’s first name.
        family_name (str): The person’s last name.
        identifiers (List): A unique string array of identifiers in
            the format [system name]:[id]
        email_addresses (List): An array of email address object hashes
            associated with the person.
        postal_addresses (List): An array of postal address object
            hashes associated with the person.
        _links (List): The links associated with this resource,
            available in the links section of the resource. Links
            that are part of the OSDI spec are typically prefixed
            with the osdi: namespace to aid in curie matching
            and readability.
        custom_fields (Dict): Key/value pairs associated with the
            person created by a user rather than a service or
            vendor.

    Attributes:
        given_name (str)The person’s first name.
        family_name (str): The person’s last name.
        identifiers (List): A unique string array of identifiers in
            the format [system name]:[id]
        email_addresses (List): An array of email address object hashes
            associated with the person.
        postal_addresses (List): An array of postal address object
            hashes associated with the person.
        _links (List): The links associated with this resource,
            available in the links section of the resource. Links
            that are part of the OSDI spec are typically prefixed
            with the osdi: namespace to aid in curie matching
            and readability.
        custom_fields (Dict): Key/value pairs associated with the
            person created by a user rather than a service or
            vendor.
    """

    def __init__(
            self,
            given_name='',
            family_name='',
            identifiers=[],
            email_addresses=[],
            postal_addresses=[],
            _links=[],
            custom_fields=[],
            created_date='',
            modified_date='',
            languages_spoken=[]
    ):
        self.given_name = given_name
        self.family_name = family_name
        self.identifiers = identifiers
        self.email_addresses = email_addresses
        self.postal_addresses = postal_addresses
        self._links = _links
        self.custom_fields = custom_fields
        self.created_date = created_date
        self.modified_date = modified_date
        self.languages_spoken = languages_spoken

    def get_actionnetwork_id(self):
        """Returns the ActionNetwork ID"""

        for i in self.identifiers:
            if i.startswith('action_network'):
                return i[len('action_network:'):]

    @staticmethod
    def load_json(dct):
        """Converts JSON person to Person object"""

        # This gets called recursively for all objects so we need
        # to filter out any objects that don't match the constructor

        for k in dct.keys():
            if k not in Person.__init__.__code__.co_varnames:
                return dct
        return Person(**dct)
