# -*- coding: utf-8 -*-
"""Management of NTFS filesystem.

Uses win32api in order to manage the Windows NTFS filesystem. Using the API directly instead of invoking the shell from
within Python was preferred as it was more efficient and more modulable.

Notes:
    For functions that ask for a 'path' parameter, it's important to use certain formats.
    We can input 'C:\\foo\\bar' (with double backslashes) or 'C:/foo/bar' (this one may not work for
    certain MS-DOS commands). Just inputting 'C:\foo\bar' (with single backslashes) will NOT work because '\f' and '\b'
    will be interpreted in a special way. For example '\t' is interpreted as a tab.

Examples:
    Instances of Directory create a directory if it doesn't already exist.

    >>> file_or_dir_exists('C:\\foo\\bar')
    False
    >>> Directory('C:\\foo\\bar')
    >>> file_or_dir_exists('C:\\foo\\bar')
    True

    >>> foo = Directory('C:/foo/bar')
"""

import os
import shutil
import win32security
import ntsecuritycon as con

from src.code.constants import WellKnownSIDs, Permissions
from typing import Any, Generator


class NotAValidPath(Exception):
    """If the path doesn't have a correct syntax."""
    pass


class NotAValidPermission(Exception):
    """If the permission given isn't amongst the predetermined permissions designed to be handled external functions."""
    pass


def file_or_dir_exists(path: str) -> bool:
    """Checks if file or directory at given path exists. Returns True if it does, False if not."""
    return os.path.exists(path)


def copy_to(source_path: str, destination_path: str, *, overwrite: bool = False) -> bool:
    """Copy file or directory to destination.

    Performs existence checks by itself. No pre-conditions.

    Args:
        source_path: Path to the directory that's going to be moved.
        destination_path: Path to where the directory is going to be copied.
        overwrite: Whether to overwrite if the destination exists (True) or not (False).

    Returns:
        True if the file or directory was copied, False if not.
    """
    exists = file_or_dir_exists(source_path)

    if exists and (overwrite or not file_or_dir_exists(destination_path)):
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.copy(source_path, destination_path)

        return True
    else:
        return False


class Directory:
    """NTFS management of a given directory.

    Attributes:
        path: Full path to the directory.
        reset_perms: Whether to reset all permissions of a directory back to default (True), or not (False).
    """

    def __init__(self, path_to_dir: str, reset_perms: bool = True) -> None:
        """Assigns a class instance to an existing directory or creates one first.

        Args:
            path_to_dir: Full path to the directory.
            reset_perms: Whether to reset the permissions of the directory (True) or not (False).
        """
        self.path: str = os.path.abspath(path_to_dir)

        if not file_or_dir_exists(self.path):
            self.create_dir(self.path)
        if reset_perms:
            self.reset_permissions()

    @property
    def path(self) -> str:
        """Getter for directory path."""
        return self._path

    # TODO Implement more rigorous path checking.
    @path.setter
    def path(self, new_path: str) -> None:
        """Setter for directory path.

        Args:
            new_path: New path of the directory.

        Returns:
            None.

        Raises:
            NotAValidPath: If the given path is not a string.
            """
        if isinstance(new_path, str):
            self._path = new_path
        else:
            raise NotAValidPath("The input is not a string.")

    @staticmethod
    def create_dir(path: str) -> None:
        """Create directory at given path. Must not already exist."""
        os.mkdir(path)

    @staticmethod
    def del_dir(path: str) -> None:
        """Delete directory at given path. Must exist."""
        shutil.rmtree(path)

    def list_dir_content(self) -> Generator[str, Any, None]:
        """Yields the contents of the current directory (not recursively)."""
        return (os.path.join(self.path, content) for content in os.listdir(self.path))

    def list_subdirectories_recurs(self) -> Generator[str, Any, None]:
        """Yields all subdirectories and subfiles including the current directory recursively (tree search)."""
        for dir_name, dir_names, file_names in os.walk(self.path):
            # Every directory name path.
            for sub_dir_name in dir_names:
                yield os.path.abspath(os.path.join(dir_name, sub_dir_name))

            # Every file path.
            for filename in file_names:
                yield os.path.abspath(os.path.join(dir_name, filename))

    def move_dir_to(self, destination: str, overwrite: bool) -> bool:
        """Move directory to path.

        Performs existence checks by itself. No pre-conditions.

        Args:
            destination: Full path of the destination of the current directory (possibility to rename as well).
            overwrite: If a file or directory is already present with the same name, option to delete it.

        Returns:
            True if the file was moved, False if not.
        """
        if (not file_or_dir_exists(destination)) or overwrite:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.move(self.path, destination)
            self.path = destination

            return True
        else:
            return False

    def reset_permissions(self, *, recursive: bool = False) -> None:
        """Resets all permissions of a file/directory and gives full control to NT Authority, Admins group.

        Args:
            recursive: Whether to reset the permissions of all subdirectories and content as well or not.

        Returns:
            None.
        """
        targets = [self.path]
        if recursive:
            targets = self.list_subdirectories_recurs()

        for target in targets:
            self._reset_permissions(target)

    def _reset_permissions(self, path: str) -> win32security.SECURITY_DESCRIPTOR:
        """Resets all permissions of a file/directory and gives full control to NT Authority, Admins group."""
        # Gets the security descriptor (sd).
        sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
        _, propagation_flags = self._set_flags(propagation=True)

        # Sets full control.
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, propagation_flags, con.FILE_ALL_ACCESS,
                                   WellKnownSIDs.NT_AUTHORITY.value)
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, propagation_flags, con.FILE_ALL_ACCESS,
                                   WellKnownSIDs.ADMINS.value)

        # Updates file security.
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)

        # Returning the security descriptor is needed for testing purposes.
        return sd

    @staticmethod
    def reset_user_permissions(path: str, user_or_group) -> win32security.SECURITY_DESCRIPTOR:
        """Resets a user/group's permissions on the current directory.

        Args:
            path: Path of the directory to reset the permissions of a user or group of.
            user_or_group: PySID object representing the SID of a user or group.

        Returns:
            Security Descriptor of directory if need be for testing purposes (checking what it returned).
        """
        sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)

        dacl = sd.GetSecurityDescriptorDacl()
        ace_count = dacl.GetAceCount()

        i = 0
        while i < ace_count:
            ace = dacl.GetAce(i)

            if type(ace) is tuple:
                user = win32security.LookupAccountSid(None, ace[-1])
            else:
                user = win32security.LookupAccountSid(None, ace)

            user_to_delete = win32security.LookupAccountSid(None, user_or_group)

            if user == user_to_delete:
                dacl.DeleteAce(i)
                ace_count -= 1
            else:
                i += 1

        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)

        return sd

    def give_permission(self,
                        user_or_group: str,
                        permissions: Permissions,
                        *,
                        recursive: bool = False) -> None:
        """Gives a specific permission on the directory to a user/group.

        Args:
            user_or_group: Name of the user/group.
            permissions: Read, Write, Modify, Modify Protected (doesn't allow deleting of parent), Full Control,
                or Full Deny.
            recursive: Whether to apply the permissions recursively on all subfiles and subdirectories

        Returns:
            None.

        Raises:
            NotAValidPermission: If the permission provided in the arguments isn't set in src.code.constants.
        """
        try:
            if permissions not in Permissions or permissions is Permissions.DELETE:
                raise NotAValidPermission("The permission isn't valid.")
        except TypeError:
            raise NotAValidPermission("The permission isn't valid.")

        targets = [self.path]
        if recursive:
            targets = self.list_subdirectories_recurs()

        user_or_group_sid = self._get_user_or_group_pysid(user_or_group)

        for target in targets:
            self.reset_user_permissions(target, user_or_group_sid)

        if permissions is Permissions.MODIFY_PROTECTED:
            for target in targets:
                self._grant_permission(user_or_group=user_or_group_sid,
                                       path=target,
                                       permissions=Permissions.MODIFY)

            # Make it so the top-level directory cannot be deleted despite MODIFY permissions.
            self._deny_permission(user_or_group=user_or_group_sid,
                                  path=self.path,
                                  permissions=Permissions.DELETE,
                                  propagation=False)
        elif permissions is Permissions.FULL_DENY:
            for target in targets:
                self._deny_permission(user_or_group=user_or_group_sid,
                                      path=target,
                                      permissions=Permissions.FULL_CONTROL)
        else:
            for target in targets:
                self._grant_permission(user_or_group=user_or_group_sid,
                                       path=target,
                                       permissions=permissions)

    @staticmethod
    def _set_flags(*, inherits: bool = False, propagation: bool = False) -> tuple[int, int]:
        """Sets propagation and inheritance flags.

        Args:
            inherits: Enables or disable inheritance from parents (Inheritance Flag).
            propagation: Enables or disable propagation of ACE to all subdirectories and subfiles (Propagation Flag).

        Returns:
            Flag information contained in the form of a tuple.
        """
        if propagation:
            # (OI)(CI)
            propagation_flags = win32security.CONTAINER_INHERIT_ACE | win32security.OBJECT_INHERIT_ACE
        else:
            propagation_flags = win32security.NO_INHERITANCE

        security_information_flags = win32security.DACL_SECURITY_INFORMATION
        if not inherits:
            # PROTECTED_DACL_SECURITY_INFORMATION disables inheritance from parent.
            security_information_flags = security_information_flags | win32security.PROTECTED_DACL_SECURITY_INFORMATION
        else:
            security_information_flags = security_information_flags | \
                                         win32security.UNPROTECTED_DACL_SECURITY_INFORMATION

        return security_information_flags, propagation_flags

    def _grant_permission(self,
                          *,
                          user_or_group,
                          path: str,
                          permissions: Permissions,
                          inherits: bool = True,
                          propagation: bool = True) -> win32security.SECURITY_DESCRIPTOR:
        """Gives a specific permission on the directory to a user/group.

        Args:
            user_or_group: PySID of the user/group.
            path: Path of the directory to modify the permissions of.
            permissions: Read, Write, Modify, Delete or Full Control.
            inherits: Enables or disable inheritance from parents (Inheritance Flag).
            propagation: Enables or disable propagation of ACE to all subdirectories and subfiles (Propagation Flag).

        Returns:
            Security Descriptor of directory if need be for testing purposes (checking what it returned).

        Raises:
            If we couldn't get the security descriptor of a file for any reason.
        """
        # Set flags.
        security_information_flags, propagation_flags = self._set_flags(inherits=inherits, propagation=propagation)

        # Gets the security descriptor (sd).
        try:
            sd = win32security.GetNamedSecurityInfo(path, win32security.SE_FILE_OBJECT,
                                                    win32security.DACL_SECURITY_INFORMATION |
                                                    win32security.UNPROTECTED_DACL_SECURITY_INFORMATION)
        except BaseException as e:
            raise OSError('Failed to read security for file: {0}. {1}'.format(path, e))

        # Gives permissions.
        print(type(sd))
        dacl = sd.GetSecurityDescriptorDacl()
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, propagation_flags, permissions.value, user_or_group)

        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetNamedSecurityInfo(path, win32security.SE_FILE_OBJECT, security_information_flags,
                                           None, None, dacl, None)

        return sd

    def _deny_permission(self,
                         *,
                         user_or_group,
                         path: str,
                         permissions: Permissions,
                         inherits: bool = True,
                         propagation: bool = True) -> win32security.SECURITY_DESCRIPTOR:
        """Denies a specific permission on the directory to a user/group.

        Args:
            user_or_group: PySID of the user/group.
            path: Path of the directory to modify the permissions of.
            permissions: Read, Write, Modify, Delete or Full Control (Full Deny).
            inherits: Enables or disable inheritance from parents (Inheritance Flag).
            propagation: Enables or disable propagation of ACE to all subdirectories and subfiles (Propagation Flag).

        Returns:
            Security Descriptor of directory if need be for testing purposes (checking what it returned).

        Raises:
            If we couldn't get the security descriptor of a file for any reason.
        """
        # Set flags.
        security_information_flags, propagation_flags = self._set_flags(inherits=inherits, propagation=propagation)

        # Gets the security descriptor (sd).
        try:
            sd = win32security.GetNamedSecurityInfo(path, win32security.SE_FILE_OBJECT,
                                                    win32security.DACL_SECURITY_INFORMATION |
                                                    win32security.UNPROTECTED_DACL_SECURITY_INFORMATION)
        except BaseException as e:
            raise OSError('Failed to read security for file: {0}. {1}'.format(path, e))

        # Gives permissions.
        dacl = sd.GetSecurityDescriptorDacl()
        dacl.AddAccessDeniedAceEx(win32security.ACL_REVISION, propagation_flags, permissions.value, user_or_group)

        sd.SetSecurityDescriptorDacl(1, dacl, 0)  # Not obligatory.
        win32security.SetNamedSecurityInfo(path, win32security.SE_FILE_OBJECT, security_information_flags,
                                           None, None, dacl, None)

        return sd

    @staticmethod
    def _get_user_or_group_pysid(user_or_group: str) -> Any:
        return win32security.LookupAccountName(None, user_or_group)[0]
