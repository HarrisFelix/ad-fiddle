import pytest

from contextlib import nullcontext as does_not_raise
from unittest.mock import patch
from src.code import share


def win32net_net_share_enum(new_resume_handle):
    return [{"netname": "foo"}, {"netname": "bar"}], 2, new_resume_handle


@pytest.mark.parametrize("share_name, new_resume_handle, result", [("foo", 0, True),
                                                                   ("foo", 1, True),
                                                                   ("void", 0, False),
                                                                   ("void", 1, None)])
def test_share_exists(share_name, new_resume_handle, result):
    copy_of_share_exists = share.share_exists

    with patch("src.code.share.win32net.NetShareEnum", return_value=win32net_net_share_enum(new_resume_handle)), \
            patch("src.code.share.share_exists", return_value=None):
        assert copy_of_share_exists("server", share_name, new_resume_handle) is result


@pytest.mark.parametrize("share_name, overwrite, expectation", [("foo", False, pytest.raises(BaseException)),
                                                                ("foo", True, does_not_raise()),
                                                                ("void", False, does_not_raise())])
def test_create_share_error_if_share_exists(share_name, overwrite, expectation):
    with expectation as e:
        with patch("src.code.share.share_exists"), patch("src.code.share.del_share"), \
                patch("src.code.share.win32security"), patch("src.code.share.win32net"):
            share.create_share("server", "C:\\foo\\bar", share_name, "", overwrite)

        if not isinstance(expectation, does_not_raise):
            assert e[0] == 2118  # Name has already been shared.


if __name__ == '__main__':
    pytest.main()
