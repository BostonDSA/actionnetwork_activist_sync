# -*- coding: utf-8 -*-
"""Converts ActionKit Excel exports to Agate tables"""

import io

import agate

class ActionKitExport:
    """ActionKitExport converts two ActionKit Excel spreadsheets.

    The reason there are two is so we can calculate who is missing in
    the new sheet and who are new members.

    Args:
        previous_file (io.IOBase): The last spreadsheet that was synced
        current_file (io.IOBase): The newest spreadsheet to be synced

    Attributes:
        previous_file (io.IOBase): The last spreadsheet that was synced
        current_file (io.IOBase): The newest spreadsheet to be synced
        previous (agate.Table): The last spreadsheet after conversion
        current (agate.Table): The newest spreadsheet after conversion
        missing_email (agate.Table): Rows that were missing an email
    """

    def __init__(self, previous_file: io.IOBase, current_file: io.IOBase):
        self.previous_file = previous_file
        self.current_file = current_file
        self.previous = None
        self.current = None
        self.missing_email = None

    def load(self) -> None:
        """Converts the spreadsheets to Agate tables"""

        if not isinstance(self.previous_file, io.IOBase):
            raise TypeError

        if not isinstance(self.current_file, io.IOBase):
            raise TypeError

        self.previous = agate.Table.from_csv(self.previous_file)
        self.current = agate.Table.from_csv(self.current_file)

    def filter_missing_email(self) -> None:
        """Strips out and saves rows that are missing emails"""
        self.missing_email = self.current.where(lambda row: row['email'] is None)
        self.previous = self.previous.where(lambda row: row['email'] is not None)
        self.current = self.current.where(lambda row: row['email'] is not None)

    def get_previous_not_in_current(self) -> agate.Table:
        """Finds rows that were missing in the current spreadsheet"""
        return self.previous.select(['email']) \
            .join(self.current, 'email', 'email', columns=['email']) \
            .where(lambda row: row['email2'] is None)
