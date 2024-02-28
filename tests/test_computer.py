import pytest

from src.code import computer
from datetime import datetime


@pytest.fixture
def now():
    return datetime.strptime('2022-11-30 01:25:50.935094', '%Y-%m-%d %H:%M:%S.%f')


def list_of_date_types():
    return [date_type for date_type in computer.TimeFormat]


@pytest.mark.parametrize("date_type", list_of_date_types())
def test_current_time(date_type):
    assert isinstance(computer.current_time(date_type), str) is True


def test__current_time(now):
    assert computer._current_time(now) == "01:25:50"


def test__curent_date(now):
    assert computer._current_date(now) == "mercredi le 30 novembre 2022"


def test__current_date_time(now):
    assert computer._current_date_time(now) == "mercredi le 30 novembre 2022 vers 01:25:50"


def test__current_timestamp(now):
    assert computer._current_timestamp(now) == "A2022-M11-J30_H01-M25-S50"


if __name__ == '__main__':
    pytest.main()
