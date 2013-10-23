# -*- encoding: utf-8 -*-

"""
    sleekxmpp.xmlstream.dns
    ~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2012 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

import socket
import logging
import random


log = logging.getLogger(__name__)


#: Global flag indicating the availability of the ``dnspython`` package.
#: Installing ``dnspython`` can be done via:
#:
#: .. code-block:: sh
#:
#:     pip install dnspython
#:
#: For Python3, installation may require installing from source using
#: the ``python3`` branch:
#:
#: .. code-block:: sh
#:
#:     git clone http://github.com/rthalley/dnspython
#:     cd dnspython
#:     git checkout python3
#:     python3 setup.py install
USE_DNSPYTHON = False
try:
    import dns.resolver
    USE_DNSPYTHON = True
except ImportError as e:
    log.debug("Could not find dnspython package. " + \
              "Not all features will be available")


def default_resolver():
    """Return a basic DNS resolver object.

    :returns: A :class:`dns.resolver.Resolver` object if dnspython
              is available. Otherwise, ``None``.
    """
    if USE_DNSPYTHON:
        return dns.resolver.get_default_resolver()
    return None


def resolve(host, port=None, service=None, proto='tcp',
            resolver=None, use_ipv6=True):
    """Peform DNS resolution for a given hostname.

    Resolution may perform SRV record lookups if a service and protocol
    are specified. The returned addresses will be sorted according to
    the SRV priorities and weights.

    If no resolver is provided, the dnspython resolver will be used if
    available. Otherwise the built-in socket facilities will be used,
    but those do not provide SRV support.

    If SRV records were used, queries to resolve alternative hosts will
    be made as needed instead of all at once.

    :param     host: The hostname to resolve.
    :param     port: A default port to connect with. SRV records may
                     dictate use of a different port.
    :param  service: Optional SRV service name without leading underscore.
    :param    proto: Optional SRV protocol name without leading underscore.
    :param resolver: Optionally provide a DNS resolver object that has
                     been custom configured.
    :param use_ipv6: Optionally control the use of IPv6 in situations
                     where it is either not available, or performance
                     is degraded. Defaults to ``True``.

    :type     host: string
    :type     port: int
    :type  service: string
    :type    proto: string
    :type resolver: :class:`dns.resolver.Resolver`
    :type use_ipv6: bool

    :return: An iterable of IP address, port pairs in the order
             dictated by SRV priorities and weights, if applicable.
    """
    if not use_ipv6:
        log.debug("DNS: Use of IPv6 has been disabled.")

    if resolver is None and USE_DNSPYTHON:
        resolver = dns.resolver.get_default_resolver()

    # An IPv6 literal is allowed to be enclosed in square brackets, but
    # the brackets must be stripped in order to process the literal;
    # otherwise, things break.
    host = host.strip('[]')

    try:
        # If `host` is an IPv4 literal, we can return it immediately.
        ipv4 = socket.inet_aton(host)
        yield (host, host, port)
    except socket.error:
        pass

    if use_ipv6:
        try:
            # Likewise, If `host` is an IPv6 literal, we can return
            # it immediately.
            if hasattr(socket, 'inet_pton'):
                ipv6 = socket.inet_pton(socket.AF_INET6, host)
                yield (host, host, port)
        except socket.error:
            pass

    # If no service was provided, then we can just do A/AAAA lookups on the
    # provided host. Otherwise we need to get an ordered list of hosts to
    # resolve based on SRV records.
    if not service:
        hosts = [(host, port)]
    else:
        hosts = get_SRV(host, port, service, proto, resolver=resolver)

    for host, port in hosts:
        results = []
        if host == 'localhost':
            if use_ipv6:
                results.append((host, '::1', port))
            results.append((host, '127.0.0.1', port))
        if use_ipv6:
            for address in get_AAAA(host, resolver=resolver):
                results.append((host, address, port))
        for address in get_A(host, resolver=resolver):
            results.append((host, address, port))

        for host, address, port in results:
            yield host, address, port


def get_A(host, resolver=None):
    """Lookup DNS A records for a given host.

    If ``resolver`` is not provided, or is ``None``, then resolution will
    be performed using the built-in :mod:`socket` module.

    :param     host: The hostname to resolve for A record IPv4 addresses.
    :param resolver: Optional DNS resolver object to use for the query.

    :type     host: string
    :type resolver: :class:`dns.resolver.Resolver` or ``None``

    :return: A list of IPv4 literals.
    """
    log.debug("DNS: Querying %s for A records." % host)

    # If not using dnspython, attempt lookup using the OS level
    # getaddrinfo() method.
    if resolver is None:
        try:
            recs = socket.getaddrinfo(host, None, socket.AF_INET,
                                                  socket.SOCK_STREAM)
            return [rec[4][0] for rec in recs]
        except socket.gaierror:
            log.debug("DNS: Error retreiving A address info for %s." % host)
            return []

    # Using dnspython:
    try:
        recs = resolver.query(host, dns.rdatatype.A)
        return [rec.to_text() for rec in recs]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        log.debug("DNS: No A records for %s" % host)
        return []
    except dns.exception.Timeout:
        log.debug("DNS: A record resolution timed out for %s" % host)
        return []
    except dns.exception.DNSException as e:
        log.debug("DNS: Error querying A records for %s" % host)
        log.exception(e)
        return []


def get_AAAA(host, resolver=None):
    """Lookup DNS AAAA records for a given host.

    If ``resolver`` is not provided, or is ``None``, then resolution will
    be performed using the built-in :mod:`socket` module.

    :param     host: The hostname to resolve for AAAA record IPv6 addresses.
    :param resolver: Optional DNS resolver object to use for the query.

    :type     host: string
    :type resolver: :class:`dns.resolver.Resolver` or ``None``

    :return: A list of IPv6 literals.
    """
    log.debug("DNS: Querying %s for AAAA records." % host)

    # If not using dnspython, attempt lookup using the OS level
    # getaddrinfo() method.
    if resolver is None:
        try:
            recs = socket.getaddrinfo(host, None, socket.AF_INET6,
                                                  socket.SOCK_STREAM)
            return [rec[4][0] for rec in recs]
        except socket.gaierror:
            log.debug("DNS: Error retreiving AAAA address " + \
                      "info for %s." % host)
            return []

    # Using dnspython:
    try:
        recs = resolver.query(host, dns.rdatatype.AAAA)
        return [rec.to_text() for rec in recs]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        log.debug("DNS: No AAAA records for %s" % host)
        return []
    except dns.exception.Timeout:
        log.debug("DNS: AAAA record resolution timed out for %s" % host)
        return []
    except dns.exception.DNSException as e:
        log.debug("DNS: Error querying AAAA records for %s" % host)
        log.exception(e)
        return []


def get_SRV(host, port, service, proto='tcp', resolver=None):
    """Perform SRV record resolution for a given host.

    .. note::

        This function requires the use of the ``dnspython`` package. Calling
        :func:`get_SRV` without ``dnspython`` will return the provided host
        and port without performing any DNS queries.

    :param     host: The hostname to resolve.
    :param     port: A default port to connect with. SRV records may
                     dictate use of a different port.
    :param  service: Optional SRV service name without leading underscore.
    :param    proto: Optional SRV protocol name without leading underscore.
    :param resolver: Optionally provide a DNS resolver object that has
                     been custom configured.

    :type     host: string
    :type     port: int
    :type  service: string
    :type    proto: string
    :type resolver: :class:`dns.resolver.Resolver`

    :return: A list of hostname, port pairs in the order dictacted
             by SRV priorities and weights.
    """
    if resolver is None:
        log.warning("DNS: dnspython not found. Can not use SRV lookup.")
        return [(host, port)]

    log.debug("DNS: Querying SRV records for %s" % host)
    try:
        recs = resolver.query('_%s._%s.%s' % (service, proto, host),
                              dns.rdatatype.SRV)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        log.debug("DNS: No SRV records for %s." % host)
        return [(host, port)]
    except dns.exception.Timeout:
        log.debug("DNS: SRV record resolution timed out for %s." % host)
        return [(host, port)]
    except dns.exception.DNSException as e:
        log.debug("DNS: Error querying SRV records for %s." % host)
        log.exception(e)
        return [(host, port)]

    if len(recs) == 1 and recs[0].target == '.':
        return [(host, port)]

    answers = {}
    for rec in recs:
        if rec.priority not in answers:
            answers[rec.priority] = []
        if rec.weight == 0:
            answers[rec.priority].insert(0, rec)
        else:
            answers[rec.priority].append(rec)

    sorted_recs = []
    for priority in sorted(answers.keys()):
        while answers[priority]:
            running_sum = 0
            sums = {}
            for rec in answers[priority]:
                running_sum += rec.weight
                sums[running_sum] = rec

            selected = random.randint(0, running_sum + 1)
            for running_sum in sums:
                if running_sum >= selected:
                    rec = sums[running_sum]
                    host = rec.target.to_text()
                    if host.endswith('.'):
                        host = host[:-1]
                    sorted_recs.append((host, rec.port))
                    answers[priority].remove(rec)
                    break

    return sorted_recs
