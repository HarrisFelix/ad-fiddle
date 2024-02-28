# -*- coding: utf-8 -*-
"""Management of Windows shares.

Uses win32api in order to manage Windows shares. Using the API directly instead of invoking the shell from within
Python was preferred as it was more efficient and more modulable.

Notes:
    For functions that ask for a 'path' parameter, it's important to use certain formats.
    We can input 'C:\\foo\\bar' (with double backslashes) or 'C:/foo/bar' (this one may not work for
    certain MS-DOS commands). Just inputting 'C:\foo\bar' (with single backslashes) will NOT work because '\f' and '\b'
    will be interpreted in a special way. For example '\t' is interpreted as a tab.

Examples:
    >>> create_share('foo.local', 'C:\\foo\\bar', 'test', 'testing share creation')

    >>> create_share('bar.local', 'C:/foo/bar', 'test', 'testing share creation')
"""

import win32net
import win32netcon
import win32security
import ntsecuritycon as con

from src.code.constants import WellKnownSIDs


def share_exists(server: str, share_name: str, resume_handle: int = 0) -> bool:
    """Checks if a share already exists.

    Args:
        server: Server on which to check the existence of a share.
        share_name: Name of the share.
        resume_handle: Should be 0. Tracks which page of information we are on if there's too much information.

    Returns:
        True if the share already exists, False if not.
    """
    all_shares, _, new_resume_handle = win32net.NetShareEnum(server, resume_handle)

    if share_name in [share['netname'] for share in all_shares]:
        return True
    # Checks if there's more data not yet retrieved.
    elif new_resume_handle:
        return share_exists(server, share_name, new_resume_handle)
    else:
        return False


def create_share(server: str,
                 path: str,
                 share_name: str,
                 remark: str,
                 overwrite: bool = True) -> None:
    """Creates a share with the information given. Must not already exist if overwrite is not True.

    Path MUST be an absolute path.

    Args:
        server: Server on which to create a share.
        path: Absolute path of the directory to share.
        share_name: Name of the share.
        remark: Comment on the share.
        overwrite: Deletes an existing share of the same name instead of returning an error (True).

    Returns:
        None.
    """
    if overwrite:
        if share_exists(server, share_name):
            del_share(server, share_name)

    # Sets security descriptor as Full Control to everyone.
    sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
    dacl = win32security.ACL()
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_ALL_ACCESS, WellKnownSIDs.EVERYONE.value)
    sd.SetSecurityDescriptorDacl(1, dacl, 0)

    # Settings of the share.
    data = {'netname': share_name,
            'type': win32netcon.STYPE_DISKTREE,
            'remark': remark,
            'permissions': 0,  # Not supported by Windows.
            'max_uses': -1,  # Unlimited.
            'current_uses': 0,
            'path': path,
            'passwd': None,  # Not supported by Windows.
            'reserved': 0,  # Has to be 0.
            'security_descriptor': sd}

    # https://learn.microsoft.com/en-us/windows/win32/api/lmshare/ns-lmshare-share_info_502
    win32net.NetShareAdd(server, 502, data)


def del_share(server: str, share_name: str) -> None:
    """Deletes a share. Must exist.

    Args:
        server: Server on which to delete a share.
        share_name: Name of the share to delete.

    Returns:
        None.
    """
    win32net.NetShareDel(server, share_name)
