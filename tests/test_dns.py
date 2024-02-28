import pytest

from contextlib import nullcontext as does_not_raise
from src.code import dns


def test_get_dns():
    assert len(dns.get_dns().split('.')) > 1


@pytest.mark.parametrize("dns_input, result", [("TEST.local", True),
                                               ("dc=TEST,dc=local", False),
                                               ("Test", False),
                                               ("", False)])
def test__is_std_dns(dns_input, result):
    assert dns._is_std_dns(dns_input) is result


@pytest.mark.parametrize("dns_input, result", [("TEST.local", False),
                                               ("dc=TEST,dc=local", True),
                                               ("Test", False),
                                               ("", False)])
def test__is_ldap_dns(dns_input, result):
    assert dns._is_ldap_dns(dns_input) is result


@pytest.mark.parametrize("dns_input, result, expectation", [("TEST.local", "dc=TEST,dc=local", does_not_raise()),
                                                            ("dc=TEST,dc=local", "TEST.local", does_not_raise()),
                                                            ("Test", None, pytest.raises(dns.NotAValidDNS))])
def test_dns_ldap_path_switcher(dns_input, result, expectation):
    with expectation:
        assert dns.dns_ldap_path_switcher(dns_input) == result


if __name__ == '__main__':
    pytest.main()
