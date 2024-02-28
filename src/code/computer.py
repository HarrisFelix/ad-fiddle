# -*- coding: utf-8 -*-
"""Management of computer variables and time."""

import locale
import win32api
import win32net

from datetime import datetime
from enum import Enum, unique, auto


# TODO IDE warning while no bug, remove once fixed.
# noinspection PyArgumentList
@unique
class TimeFormat(Enum):
    TIME = auto()
    DATE = auto()
    DATE_TIME = auto()
    TIMESTAMP = auto()


def current_time(date_type: TimeFormat = TimeFormat.DATE_TIME) -> str:
    """Returns system time in desired format.

    Args:
        date_type: Wanted time format.

    Returns:
        Formatted system time.
    """
    # French dates.
    locale.setlocale(locale.LC_ALL, 'fr_FR')

    now = datetime.now()

    if date_type is TimeFormat.TIME:
        return _current_time(now)
    elif date_type is TimeFormat.DATE:
        return _current_date(now)
    elif date_type is TimeFormat.DATE_TIME:
        return _current_date_time(now)
    elif date_type is TimeFormat.TIMESTAMP:
        return _current_timestamp(now)


def _current_time(now: datetime.now) -> str:
    """Returns time.

    Notes:
        For now = "2022-11-30 01:25:50.935094", returns '01:25:50'.
    """
    return now.strftime("%X")


def _current_date(now: datetime.now) -> str:
    """Returns date.

    Notes:
        For now = "2022-11-30 01:25:50.935094", returns 'mercredi le 30 novembre 2022'.
    """
    return f'{now.strftime("%A")} le {now.strftime("%d")} {now.strftime("%B")} {now.strftime("%Y")}'


def _current_date_time(now: datetime.now) -> str:
    """Returns date and time.

    Notes:
        For now = "2022-11-30 01:25:50.935094", returns 'mercredi le 30 novembre 2022 vers 01:25:50'.
    """
    return f"{_current_date(now)} vers {_current_time(now)}"


def _current_timestamp(now: datetime.now) -> str:
    """Returns current timestamp.

    Notes:
        For now = "2022-11-30 01:25:50.935094", returns 'A2022-M11-J30_H01-M25-S50'.
    """
    return "A{}-M{}-J{}_H{}-M{}-S{}".format(now.strftime("%Y"),
                                            now.strftime("%m"),
                                            now.strftime("%d"),
                                            now.strftime("%H"),
                                            now.strftime("%M"),
                                            now.strftime("%S"))


def netbios_name() -> str:
    """Returns the NetBIOS name of the domain (or workgroup) that the computer belongs to."""
    return win32api.GetDomainName()


def computer_name() -> str:
    """Returns computer name."""
    return win32api.GetComputerName()


def windows_version() -> int:
    """Returns the NT version of the Windows OS."""
    return win32api.GetVersionEx(0)[0]


def is_domain_controller() -> bool:
    """Check if the current system is a primary domain controller."""
    return win32net.NetGetDCName()[2:] == computer_name()
