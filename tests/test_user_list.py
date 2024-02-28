import pytest

from unittest.mock import patch, mock_open
from src.code import user_list


def csv_correct_data():
    return "one,one,S1,01/01/2001\ntwo,two,S2,02/02/2002\n"


def lst_correct_data():
    return [{"sn": "one", "givenName": "one", "class": "S1", "birthday": "01/01/2001"},
            {"sn": "two", "givenName": "two", "class": "S2", "birthday": "02/02/2002"}]


@pytest.mark.parametrize("read_data, result", [(csv_correct_data(), lst_correct_data()),
                                               (csv_correct_data().replace(',', ';'), lst_correct_data()),
                                               ("", []),
                                               ("incorrect", [])])
def test__file_content_to_lst(read_data, result):
    with patch("builtins.open", mock_open(read_data=read_data)):
        with open("/dev/null") as file:
            user_lst = user_list.__file_content_to_lst__(file)

    assert user_lst == result


@pytest.mark.parametrize("path, result", [("valid_path", list),
                                          ("invalid_path?", type(None))])
def test_file_to_lst_returns_none_if_invalid_path(path, result):
    if path == "valid_path":
        with patch("builtins.open", mock_open(read_data=csv_correct_data())) as mock_file:
            assert isinstance(user_list.file_to_lst(path), result)
        mock_file.assert_called_with(path)
    else:
        assert isinstance(user_list.file_to_lst(path), result)


if __name__ == '__main__':
    pytest.main()
