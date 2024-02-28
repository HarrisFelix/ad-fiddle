import pytest

from src.code import constants


def test_all_sids_valid():
    for sid in constants.WellKnownSIDs:
        assert sid.value.IsValid() is True


@pytest.mark.parametrize("permission, result", [(constants.Permissions.READ, 1179785),
                                                (constants.Permissions.READ_WRITE, 1180063),
                                                (constants.Permissions.DELETE, 65536),
                                                (constants.Permissions.MODIFY, -1072496480),
                                                (constants.Permissions.FULL_CONTROL, 2032127)])
def test_all_permissions_correct(permission, result):
    for perm in constants.Permissions:
        if perm is permission:
            assert perm.value == result


if __name__ == '__main__':
    pytest.main()
