# -*- coding: utf-8 -*-
"""Converts a file into a list of dictionaries."""

from typing import TextIO


def __file_content_to_lst__(file: TextIO) -> list[dict] | list[None]:
    """Converts a CSV into a Python list of dictionaries.

    Args:
        file: File to read from.

    Returns:
        The same file as a list of dictionaries, or an empty list if the file isn't well formatted.
    """
    user_lst = []

    try:
        for line in file:
            if line.count(';') >= line.count(','):
                line = line.split(';')
            else:
                line = line.split(',')

            user_lst.append({'sn': line[0],
                             'givenName': line[1],
                             'class': line[2],
                             'birthday': line[3].strip()})  # removes \n

        return user_lst
    except IndexError:
        return []


def file_to_lst(file_path: str) -> list[dict] | None:
    """Converts a CSV into a Python list of dictionaries.

    Args:
        file_path: Path of the file to read from.

    Returns:
        The same file as a list of dictionaries, or None if the file doesn't exist.
    """
    try:
        with open(file_path) as file:
            user_lst = __file_content_to_lst__(file)

        return user_lst
    except (FileNotFoundError, OSError):
        return None
