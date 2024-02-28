# -*- coding: utf-8 -*-
"""Management of DNS (format and retrieval)."""

import win32api
import win32con


class NotAValidDNS(Exception):
    """If the DNS is not valid in standard or LDAP mode."""
    pass


def get_dns() -> str:
    """Gets the DNS of the current machine."""
    return win32api.GetComputerNameEx(win32con.ComputerNameDnsDomain)


def _is_std_dns(dns: str) -> bool:
    """Checks if the DNS is in standard or LDAP mode.

    Standard would be 'mynetwork.com' | LDAP mode would be 'dc=mynetwork,dc=com'.

    Args:
        dns: The DNS to check if it's in standard mode.

    Returns:
        Whether the DNS is in standard mode (True) or not (False).
    """
    if dns:
        # Splits by dots and checks if the list contains more than one element.
        dns = dns.split('.')

        if not len(dns) > 1:
            return False
        else:
            return True
    else:
        return False


def _is_ldap_dns(dns: str) -> bool:
    """Checks if the DNS is in standard or LDAP mode.

    Standard would be 'mynetwork.com' | LDAP mode would be 'dc=mynetwork,dc=com'.

    Args:
        dns: The DNS to check if it's in LDAP mode.

    Returns:
        Whether the DNS is in LDAP mode (True) or not (False).
    """
    if dns:
        dns = dns.split(',')

        for e in dns:
            if not e[:3] == 'dc=':
                return False
        return True
    else:
        return False


def dns_ldap_path_switcher(dns: str) -> str | None:
    """Checks the mode of the DNS (STD or LDAP) then convert it into the other mode (STD <-> LDAP).

    Args:
        dns: DNS to convert.

    Returns:
        Nothing if the format is not recognized. Else returns the DNS in the converted mode.

    Raises:
        NotAValidDNS: If DNS provided is not valid.
    """
    if _is_ldap_dns(dns):
        dns = dns.split(',')
        dns = '.'.join(dns)

        return dns.replace('dc=', '')
    elif _is_std_dns(dns):
        dns = dns.split('.')
        dns = ',dc='.join(dns)

        return 'dc={}'.format(dns)
    else:
        raise NotAValidDNS("Not a valid DNS.")
