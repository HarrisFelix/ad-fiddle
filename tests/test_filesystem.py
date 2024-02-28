import pytest
import win32security

from contextlib import nullcontext as does_not_raise
from unittest.mock import patch
from src.code import filesystem
from src.code.constants import WellKnownSIDs, Permissions

DACL_SECURITY_INFO = win32security.DACL_SECURITY_INFORMATION | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION
DACL_P_SECURITY_INFO = win32security.DACL_SECURITY_INFORMATION
SDDL = win32security.SDDL_REVISION_1
INHERITS_FLAGS = 536870916
NO_INHERITS_FLAGS = -2147483644
PROPAGATION_FLAGS = 3
NO_PROPAGATION_FLAGS = 0


class DACL:
    """EV stands for Everyone."""
    DEFAULT = "D:(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)"
    READ_EV = DEFAULT + "(A;OICI;FR;;;WD)"
    READ_WRITE_EV = DEFAULT + "(A;OICI;0x12019f;;;WD)"
    MODIFY_EV = DEFAULT + "(A;OICI;0xc01300a0;;;WD)"
    FULL_CONTROL_EV = DEFAULT + "(A;OICI;FA;;;WD)"
    FULL_DENY_EV = "D:(D;OICI;FA;;;WD)" + DEFAULT[2:]
    DENY_DELETE_EV = "D:(D;;SD;;;WD)" + DEFAULT[2:]


def directory_tree_as_lst():
    return ["C:/foo/bar/dir/1.txt",
            "C:/foo/bar/dir/2.txt",
            "C:/foo/bar/1.txt",
            "C:/foo/bar/2.txt",
            "C:/foo/dir/bar/1.txt",
            "C:/foo/dir/1.txt",
            "C:/foo/1.txt",
            "C:/foo/2.txt"]


@pytest.fixture
def directory_structure(fs):
    for file in directory_tree_as_lst():
        fs.create_file(file)

    return fs


@pytest.fixture
def directory(directory_structure):
    return filesystem.Directory("C:/foo", False)


@pytest.mark.parametrize("path, result", [("C:/foo", True),
                                          ("C:/foo/1.txt", True),
                                          ("", False),
                                          ("C:/void", False)])
def test_file_or_dir_exists(path, result, directory_structure):
    assert filesystem.file_or_dir_exists(path) == result


@pytest.mark.parametrize("source_exists, destination_exists, overwrite, result", [(True, True, True, True),
                                                                                  (False, True, True, False),
                                                                                  (True, False, True, True),
                                                                                  (True, True, False, False),
                                                                                  (False, False, True, False),
                                                                                  (False, True, False, False),
                                                                                  (True, False, False, True),
                                                                                  (False, False, False, False)])
def test_copy_to_return_conditions(source_exists, destination_exists, overwrite, result):
    with patch("src.code.filesystem.file_or_dir_exists", side_effect=[source_exists, destination_exists]):
        with patch("src.code.filesystem.os"), patch("src.code.filesystem.shutil"):
            assert filesystem.copy_to("C:/foo", "C:/bar", overwrite=overwrite) is result


@pytest.mark.parametrize("already_exists, reset_perms, calls", [(True, True, (0, 1)),
                                                                (False, True, (1, 1)),
                                                                (True, False, (0, 0)),
                                                                (False, False, (1, 0))])
def test_directory_instance_init_method(already_exists, reset_perms, calls):
    with patch("src.code.filesystem.file_or_dir_exists", return_value=already_exists), \
            patch("src.code.filesystem.Directory.create_dir") as mock_create, \
            patch("src.code.filesystem.Directory.reset_permissions") as mock_reset:
        filesystem.Directory("C:/foo", reset_perms)

        assert mock_create.call_count == calls[0]
        assert mock_reset.call_count == calls[1]


@pytest.mark.parametrize("path, expectation", [("C:/foo", does_not_raise()),
                                               (None, pytest.raises(filesystem.NotAValidPath))])
def test_setter_for_directory_path(path, expectation, directory):
    with expectation:
        directory.path = path


def test_list_dir_content(directory, directory_structure):
    assert len(list(directory.list_dir_content())) == 4


def test_list_subdirectories_recurs(directory, directory_structure):
    assert len(list(directory.list_subdirectories_recurs())) == 12


@pytest.mark.parametrize("destination_exists, overwrite, result", [(True, True, True),
                                                                   (False, True, True),
                                                                   (True, False, False),
                                                                   (False, False, True)])
def test_move_dir_to_return_conditions(destination_exists, overwrite, result, directory):
    with patch("src.code.filesystem.file_or_dir_exists", return_value=destination_exists), \
            patch("src.code.filesystem.os"), patch("src.code.filesystem.shutil"):
        assert directory.move_dir_to('C:/foo/path', overwrite=overwrite) is result


@pytest.mark.parametrize("recursive, calls", [(False, 1), (True, 12)])
def test_reset_permissions_files_acted_upon(recursive, calls, directory, directory_structure):
    with patch("src.code.filesystem.Directory._reset_permissions") as mock_fn:
        directory.reset_permissions(recursive=recursive)

        assert mock_fn.call_count == calls


def test_reset_permission_of_single_dir(directory):
    with patch("src.code.filesystem.win32security.GetFileSecurity", return_value=win32security.SECURITY_DESCRIPTOR()), \
            patch("src.code.filesystem.win32security.SetFileSecurity"):
        sd = directory._reset_permissions('C:/foo')
        str_sd = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(sd, win32security.SDDL_REVISION_1,
                                                                                   DACL_SECURITY_INFO)

        assert str_sd == DACL.DEFAULT


@pytest.mark.parametrize("str_sd", [DACL.DEFAULT, DACL.READ_EV, DACL.READ_WRITE_EV, DACL.MODIFY_EV,
                                    DACL.FULL_CONTROL_EV, DACL.FULL_DENY_EV, DACL.DENY_DELETE_EV])
def test_reset_specific_user_or_group_permission(str_sd, directory):
    with patch("src.code.filesystem.win32security.GetFileSecurity",
               return_value=win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(DACL.DEFAULT, SDDL)), \
            patch("src.code.filesystem.win32security.SetFileSecurity"):
        sd = directory.reset_user_permissions(path=directory.path,
                                              user_or_group=WellKnownSIDs.EVERYONE.value)
        str_sd = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(sd, SDDL, DACL_P_SECURITY_INFO)

        assert str_sd == DACL.DEFAULT


@pytest.mark.parametrize("inherits, propagation, result", [(True, True, (INHERITS_FLAGS, PROPAGATION_FLAGS)),
                                                           (True, False, (INHERITS_FLAGS, NO_PROPAGATION_FLAGS)),
                                                           (False, True, (NO_INHERITS_FLAGS, PROPAGATION_FLAGS)),
                                                           (False, False, (NO_INHERITS_FLAGS, NO_PROPAGATION_FLAGS))])
def test_set_flags(inherits, propagation, result):
    assert filesystem.Directory._set_flags(inherits=inherits, propagation=propagation) == result


@pytest.mark.parametrize("permission, expectation",
                         [(Permissions.READ, does_not_raise()),
                          (Permissions.READ_WRITE, does_not_raise()),
                          (Permissions.MODIFY, does_not_raise()),
                          (Permissions.MODIFY_PROTECTED, does_not_raise()),
                          (Permissions.FULL_CONTROL, does_not_raise()),
                          (Permissions.FULL_DENY, does_not_raise()),
                          (Permissions.DELETE, pytest.raises(filesystem.NotAValidPermission)),
                          (None, pytest.raises(filesystem.NotAValidPermission))])
def test_give_permissions_returns_error_if_invalid_perm(permission: Permissions, expectation, directory):
    with expectation:
        with patch("src.code.filesystem.Directory.reset_user_permissions"), patch("src.code.filesystem.win32security"):
            directory.give_permission("null", permission)


@pytest.mark.parametrize("permission, calls",
                         [(Permissions.READ, (1, 0)),
                          (Permissions.READ_WRITE, (1, 0)),
                          (Permissions.MODIFY, (1, 0)),
                          (Permissions.MODIFY_PROTECTED, (1, 1)),
                          (Permissions.FULL_CONTROL, (1, 0)),
                          (Permissions.FULL_DENY, (0, 1))])
def test_give_permissions_gives_correct_permission(permission, calls, directory):
    with patch("src.code.filesystem.Directory.reset_user_permissions"), patch("src.code.filesystem.win32security"), \
            patch("src.code.filesystem.Directory._grant_permission") as mock_grant, \
            patch("src.code.filesystem.Directory._deny_permission") as mock_deny:
        directory.give_permission("null", permission)

        assert mock_grant.call_count == calls[0]
        assert mock_deny.call_count == calls[1]


@pytest.mark.parametrize("permission, result", [(Permissions.READ, DACL.READ_EV),
                                                (Permissions.READ_WRITE, DACL.READ_WRITE_EV),
                                                (Permissions.MODIFY, DACL.MODIFY_EV),
                                                (Permissions.FULL_CONTROL, DACL.FULL_CONTROL_EV)])
def test_grant_permission_works(permission, result, directory):
    with patch("src.code.filesystem.win32security.GetNamedSecurityInfo",
               return_value=win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(DACL.DEFAULT, SDDL)), \
            patch("src.code.filesystem.win32security.SetNamedSecurityInfo"):
        sd = directory._grant_permission(user_or_group=WellKnownSIDs.EVERYONE.value,
                                         path=directory.path,
                                         permissions=permission)
        str_sd = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(sd, SDDL, DACL_SECURITY_INFO)

        assert str_sd == result


@pytest.mark.parametrize("permission, propagation, result", [(Permissions.FULL_CONTROL, True, DACL.FULL_DENY_EV),
                                                             (Permissions.DELETE, False, DACL.DENY_DELETE_EV)])
def test_deny_permission_works(permission, propagation, result, directory):
    with patch("src.code.filesystem.win32security.GetNamedSecurityInfo",
               return_value=win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(DACL.DEFAULT, SDDL)), \
            patch("src.code.filesystem.win32security.SetNamedSecurityInfo"):
        sd = directory._deny_permission(user_or_group=WellKnownSIDs.EVERYONE.value,
                                        path=directory.path,
                                        permissions=permission,
                                        propagation=propagation)
        str_sd = win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(sd, SDDL, DACL_SECURITY_INFO)

        assert str_sd == result


if __name__ == '__main__':
    pytest.main()
