# -*- coding: utf-8 -*-
"""Management of Windows Active Directory.

Pyad was chosen instead of the alternatives (ldap3, win32net) due to the possibility to work with non SSL-encrypted
servers and how complete it was to manage all aspects of the AD (impossible to create an OU with win32net...).
"""

import dns
import collections.abc

from pyad import aduser as adu, adcontainer as adc, adgroup as adg, adobject as ado, adquery as adq
from enum import Enum, unique, auto


@unique
class GroupScope(Enum):
    """The possible scopes for a group."""
    LOCAL = "LOCAL"
    GLOBAL = "GLOBAL"
    UNIVERSAL = "UNIVERSAL"


# TODO IDE warning while no bug, remove once fixed.
# noinspection PyArgumentList
@unique
class ObjectType(Enum):
    """The possible object types for a search."""
    ALL = auto()
    OU = auto()
    USER_OR_GROUP = auto()
    USER = auto()
    GROUP = auto()
    COMPUTER = auto()


def object_from_dn(full_dn: str) -> ado.ADObject:
    """Retrieves an object (user_or_group, group) from the AD then transforms it into a Python object. Must exist."""
    return ado.ADObject.from_dn(full_dn)


def user_from_dn(full_dn: str) -> adu.ADUser:
    """Retrieves a user_or_group from the AD then transforms it into a Python object. Must exist."""
    return adu.ADUser.from_dn(full_dn)


def group_from_dn(full_dn: str) -> adg.ADGroup:
    """Retrieves a group from the AD then transforms it into a Python object. Must exist."""
    return adg.ADGroup.from_dn(full_dn)


def ou_from_dn(full_dn: str) -> adc.ADContainer | None:
    """Retrieves an OU from the AD then transforms it into a Python object"""
    return adc.ADContainer.from_dn(full_dn)


def del_object(obj: ado.ADObject | adc.ADContainer) -> None:
    """Deletes an object (ou, user_or_group, group) in the AD. Must exist.

    It's IMPORTANT to note that you CAN'T delete a pyad object placed directly at the root distinguished name.
    Additionally, we use recursion if the object we're deleting is an Organizational Unit, as pyad can't
    automatically delete children.

    Args:
        obj:  Object (group, user, OU) to delete.

    Returns:
        None.
    """
    if obj.type == 'organizationalUnit':
        for child_obj in obj.get_children():
            del_object(child_obj)

    obj.delete()


def create_user(upn_name: str,
                parent_ou: adc.ADContainer,
                password: str,
                attributes: dict = None,
                default_upn_suffix: str = dns.get_dns()) -> adu.ADUser:
    """Creates a new user_or_group (must not already exist) in the AD with flag set to 512.

    The user_or_group is enabled by default.
    The UPN must be under 20 characters long AT MOST, because the programs also assigns it to the sAMAccountName.

    Args:
        upn_name: Set the UserPrincipalName and the sAMAccountName of the object (login name).
        parent_ou: The OU where we are going to create the user_or_group in.
        password: The password of the user_or_group, has to be compliant with AD password requirements.
        attributes: Attributes of the user_or_group.
        default_upn_suffix: UPN suffix of the object.

    Returns:
        The created user_or_group.
    """
    if attributes is None:
        attributes = {}
    attributes['sAMAccountName'] = upn_name

    user = adu.ADUser.create(name=upn_name,
                             container_object=parent_ou,
                             password=password,
                             upn_suffix=default_upn_suffix,
                             optional_attributes=attributes)

    user.set_user_account_control_setting("PASSWD_NOTREQD", False)
    user.force_pwd_change_on_login()

    return user


def create_group(group_name: str,
                 parent_ou: adc.ADContainer,
                 group_type: GroupScope,
                 attributes: dict = None) -> adg.ADGroup | None:
    """Creates a new group in the AD.

    Args:
        group_name: The name of the group.
        parent_ou: The OU where the group is going to be created in.
        group_type: The scope of the group, named group_type because of a namespace issue in the function otherwise.
        attributes: Attributes of the group (usually the description).

    Returns:
        Newly created group or nothing if the group wasn't created for any reason.
    """
    if attributes is None:
        attributes = {}

    if group_type is GroupScope.UNIVERSAL:
        group_scope = GroupScope.UNIVERSAL.value
    elif group_type is GroupScope.GLOBAL:
        group_scope = GroupScope.GLOBAL.value
    else:
        group_scope = GroupScope.LOCAL.value

    group = adg.ADGroup.create(group_name, parent_ou, scope=group_scope, optional_attributes=attributes)

    return group


def create_ou(ou_name: str, parent_ou: adc.ADContainer, attributes: dict = None) -> adc.ADContainer:
    """Creates a new OU in the AD. Must not already exist.

    Args:
        ou_name: Name of the new OU.
        parent_ou: OU where we are going to create a new OU in.
        attributes: Attributes of the OU (usually the description).

    Returns:
        Newly created OU.
    """
    if attributes is None:
        attributes = {}

    return parent_ou.create_container(ou_name, optional_attributes=attributes)


def add_object_to_group(obj: ado.ADObject, group: adg.ADGroup) -> None:
    """Adds an object (user_or_group or group) to a group. Must not already be present."""
    obj.add_to_group(group)


def rem_object_from_group(obj: ado.ADObject, group: adg.ADGroup) -> None:
    """Removes an object (user_or_group or group) to a group. Must be present."""
    obj.remove_from_group(group)


def exists_in_group(obj: ado.ADObject, group: adg.ADGroup) -> bool:
    """Checks if an object (user_or_group or group) is already a member of a group.

    Args:
        obj: Object to check the presence of.
        group: Group on which to check the presence of.

    Returns:
        True if object is present, False if not.
    """
    group_members = group.get_members()

    for member in group_members:
        # Hash because if we check directly obj == member, it can't tell they are the same
        if hash(obj) == hash(member):
            return True
    return False


def exists_in_ad(full_dn: str) -> bool:
    """Checks if a distinguished name (ou=FOO,dc=BAR,dc=com) exists in the AD.

    Args:
        full_dn: Full Distinguished Name of the object to check the existence of.

    Returns:
        True if the object exists, False if not.
    """
    q = adq.ADQuery()

    q.execute_query(
        attributes=["distinguishedName"],
        where_clause="distinguishedName = '{}'".format(full_dn)
    )

    if q.get_row_count() == 1:
        return True
    else:
        return False


def list_ad_objects(object_type: ObjectType = ObjectType.ALL,
                    search_return_attributes: list[str] = None) -> collections.abc.Iterable | None:
    """Searches one or multiple object types in the AD.

    Args:
        object_type: Whether it's a user_or_group, group, OU, computer...
        search_return_attributes: Which attributes of the found objects are going to be put in a dictionary.

    Returns:
        Results of the search query, or nothing if an error was raised.
    """
    if search_return_attributes is None:
        search_return_attributes = ["distinguishedName"]

    search_type = {
        ObjectType.ALL: None,
        ObjectType.OU: "objectClass = 'organizationalUnit",
        ObjectType.USER_OR_GROUP: "objectClass = 'user_or_group' or objectClass = 'group'",
        ObjectType.USER: "objectClass = 'user_or_group'",
        ObjectType.GROUP: "objectClass = 'group'",
        ObjectType.COMPUTER: "objectClass = 'computer'"
    }

    try:
        q = adq.ADQuery()

        q.execute_query(
            attributes=search_return_attributes,
            where_clause=search_type[object_type]
        )

        return q.get_results()
    except KeyError as e:
        print(e)
    except BaseException as e:
        print(e)


def move_object_to(obj: ado.ADObject, ou: adc.ADContainer) -> None:
    """Moves an object to a different OU."""
    obj.move(ou)


def modify_object_attributes(obj: ado.ADObject, attributes: dict) -> None:
    """Modifies the attributes of an object."""
    obj.update_attributes(attributes)
