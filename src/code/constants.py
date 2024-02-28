# -*- coding: utf-8 -*-
"""User related constants."""

import win32api
import win32security
import ntsecuritycon as con

from enum import Enum, unique, auto


class WellKnownSIDs(Enum):
    """SIDs of the main user types (for cross-language compatibility)."""
    NT_AUTHORITY = win32security.GetBinarySid('S-1-5-18')
    ADMINS = win32security.GetBinarySid('S-1-5-32-544')
    CURRENT_USER = win32security.LookupAccountName(None, win32api.GetUserName())[0]
    EVERYONE = win32security.GetBinarySid('S-1-1-0')


# TODO IDE warning while no bug, remove once fixed.
# noinspection PyArgumentList
@unique
class Permissions(Enum):
    """User permissions."""
    READ = con.FILE_GENERIC_READ
    READ_WRITE = con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE
    DELETE = con.DELETE
    MODIFY = con.GENERIC_READ | con.GENERIC_WRITE | con.FILE_GENERIC_EXECUTE | con.DELETE
    FULL_CONTROL = con.FILE_ALL_ACCESS

    # Implementation logic by the functions that use them.
    MODIFY_PROTECTED = auto()
    FULL_DENY = auto()

