# -*- coding: utf-8 -*-
"""
    sleekxmpp.jid
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module allows for working with Jabber IDs (JIDs).

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

from __future__ import unicode_literals

import re
import socket
import stringprep
import threading
import encodings.idna

from sleekxmpp.util import stringprep_profiles
from sleekxmpp.thirdparty import OrderedDict

#: These characters are not allowed to appear in a JID.
ILLEGAL_CHARS = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r' + \
                '\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19' + \
                '\x1a\x1b\x1c\x1d\x1e\x1f' + \
                ' !"#$%&\'()*+,./:;<=>?@[\\]^_`{|}~\x7f'

#: The basic regex pattern that a JID must match in order to determine
#: the local, domain, and resource parts. This regex does NOT do any
#: validation, which requires application of nodeprep, resourceprep, etc.
JID_PATTERN = re.compile(
    "^(?:([^\"&'/:<>@]{1,1023})@)?([^/@]{1,1023})(?:/(.{1,1023}))?$"
)

#: The set of escape sequences for the characters not allowed by nodeprep.
JID_ESCAPE_SEQUENCES = set(['\\20', '\\22', '\\26', '\\27', '\\2f',
                            '\\3a', '\\3c', '\\3e', '\\40', '\\5c'])

#: A mapping of unallowed characters to their escape sequences. An escape
#: sequence for '\' is also included since it must also be escaped in
#: certain situations.
JID_ESCAPE_TRANSFORMATIONS = {' ': '\\20',
                              '"': '\\22',
                              '&': '\\26',
                              "'": '\\27',
                              '/': '\\2f',
                              ':': '\\3a',
                              '<': '\\3c',
                              '>': '\\3e',
                              '@': '\\40',
                              '\\': '\\5c'}

#: The reverse mapping of escape sequences to their original forms.
JID_UNESCAPE_TRANSFORMATIONS = {'\\20': ' ',
                                '\\22': '"',
                                '\\26': '&',
                                '\\27': "'",
                                '\\2f': '/',
                                '\\3a': ':',
                                '\\3c': '<',
                                '\\3e': '>',
                                '\\40': '@',
                                '\\5c': '\\'}

JID_CACHE = OrderedDict()
JID_CACHE_LOCK = threading.Lock()
JID_CACHE_MAX_SIZE = 1024

def _cache(key, parts, locked):
    JID_CACHE[key] = (parts, locked)
    if len(JID_CACHE) > JID_CACHE_MAX_SIZE:
        with JID_CACHE_LOCK:
            while len(JID_CACHE) > JID_CACHE_MAX_SIZE:
                found = None
                for key, item in JID_CACHE.iteritems():
                    if not item[1]: # if not locked
                        found = key
                        break
                if not found: # more than MAX_SIZE locked
                    # warn?
                    break
                del JID_CACHE[found]

# pylint: disable=c0103
#: The nodeprep profile of stringprep used to validate the local,
#: or username, portion of a JID.
nodeprep = stringprep_profiles.create(
    nfkc=True,
    bidi=True,
    mappings=[
        stringprep_profiles.b1_mapping,
        stringprep.map_table_b2],
    prohibited=[
        stringprep.in_table_c11,
        stringprep.in_table_c12,
        stringprep.in_table_c21,
        stringprep.in_table_c22,
        stringprep.in_table_c3,
        stringprep.in_table_c4,
        stringprep.in_table_c5,
        stringprep.in_table_c6,
        stringprep.in_table_c7,
        stringprep.in_table_c8,
        stringprep.in_table_c9,
        lambda c: c in ' \'"&/:<>@'],
    unassigned=[stringprep.in_table_a1])

# pylint: disable=c0103
#: The resourceprep profile of stringprep, which is used to validate
#: the resource portion of a JID.
resourceprep = stringprep_profiles.create(
    nfkc=True,
    bidi=True,
    mappings=[stringprep_profiles.b1_mapping],
    prohibited=[
        stringprep.in_table_c12,
        stringprep.in_table_c21,
        stringprep.in_table_c22,
        stringprep.in_table_c3,
        stringprep.in_table_c4,
        stringprep.in_table_c5,
        stringprep.in_table_c6,
        stringprep.in_table_c7,
        stringprep.in_table_c8,
        stringprep.in_table_c9],
    unassigned=[stringprep.in_table_a1])


def _parse_jid(data):
    """
    Parse string data into the node, domain, and resource
    components of a JID, if possible.

    :param string data: A string that is potentially a JID.

    :raises InvalidJID:

    :returns: tuple of the validated local, domain, and resource strings
    """
    match = JID_PATTERN.match(data)
    if not match:
        raise InvalidJID('JID could not be parsed')

    (node, domain, resource) = match.groups()

    node = _validate_node(node)
    domain = _validate_domain(domain)
    resource = _validate_resource(resource)

    return node, domain, resource


def _validate_node(node):
    """Validate the local, or username, portion of a JID.

    :raises InvalidJID:

    :returns: The local portion of a JID, as validated by nodeprep.
    """
    try:
        if node is not None:
            node = nodeprep(node)

            if not node:
                raise InvalidJID('Localpart must not be 0 bytes')
            if len(node) > 1023:
                raise InvalidJID('Localpart must be less than 1024 bytes')
            return node
    except stringprep_profiles.StringPrepError:
        raise InvalidJID('Invalid local part')


def _validate_domain(domain):
    """Validate the domain portion of a JID.

    IP literal addresses are left as-is, if valid. Domain names
    are stripped of any trailing label separators (`.`), and are
    checked with the nameprep profile of stringprep. If the given
    domain is actually a punyencoded version of a domain name, it
    is converted back into its original Unicode form. Domains must
    also not start or end with a dash (`-`).

    :raises InvalidJID:

    :returns: The validated domain name
    """
    ip_addr = False

    # First, check if this is an IPv4 address
    try:
        socket.inet_aton(domain)
        ip_addr = True
    except socket.error:
        pass

    # Check if this is an IPv6 address
    if not ip_addr and hasattr(socket, 'inet_pton'):
        try:
            socket.inet_pton(socket.AF_INET6, domain.strip('[]'))
            domain = '[%s]' % domain.strip('[]')
            ip_addr = True
        except socket.error:
            pass

    if not ip_addr:
        # This is a domain name, which must be checked further

        if domain and domain[-1] == '.':
            domain = domain[:-1]

        domain_parts = []
        for label in domain.split('.'):
            try:
                label = encodings.idna.nameprep(label)
                encodings.idna.ToASCII(label)
                pass_nameprep = True
            except UnicodeError:
                pass_nameprep = False

            if not pass_nameprep:
                raise InvalidJID('Could not encode domain as ASCII')

            if label.startswith('xn--'):
                label = encodings.idna.ToUnicode(label)

            for char in label:
                if char in ILLEGAL_CHARS:
                    raise InvalidJID('Domain contains illegar characters')

            if '-' in (label[0], label[-1]):
                raise InvalidJID('Domain started or ended with -')

            domain_parts.append(label)
        domain = '.'.join(domain_parts)

    if not domain:
        raise InvalidJID('Domain must not be 0 bytes')
    if len(domain) > 1023:
        raise InvalidJID('Domain must be less than 1024 bytes')

    return domain


def _validate_resource(resource):
    """Validate the resource portion of a JID.

    :raises InvalidJID:

    :returns: The local portion of a JID, as validated by resourceprep.
    """
    try:
        if resource is not None:
            resource = resourceprep(resource)

            if not resource:
                raise InvalidJID('Resource must not be 0 bytes')
            if len(resource) > 1023:
                raise InvalidJID('Resource must be less than 1024 bytes')
            return resource
    except stringprep_profiles.StringPrepError:
        raise InvalidJID('Invalid resource')


def _escape_node(node):
    """Escape the local portion of a JID."""
    result = []

    for i, char in enumerate(node):
        if char == '\\':
            if ''.join((node[i:i+3])) in JID_ESCAPE_SEQUENCES:
                result.append('\\5c')
                continue
        result.append(char)

    for i, char in enumerate(result):
        if char != '\\':
            result[i] = JID_ESCAPE_TRANSFORMATIONS.get(char, char)

    escaped = ''.join(result)

    if escaped.startswith('\\20') or escaped.endswith('\\20'):
        raise InvalidJID('Escaped local part starts or ends with "\\20"')

    _validate_node(escaped)

    return escaped


def _unescape_node(node):
    """Unescape a local portion of a JID.

    .. note::
        The unescaped local portion is meant ONLY for presentation,
        and should not be used for other purposes.
    """
    unescaped = []
    seq = ''
    for i, char in enumerate(node):
        if char == '\\':
            seq = node[i:i+3]
            if seq not in JID_ESCAPE_SEQUENCES:
                seq = ''
        if seq:
            if len(seq) == 3:
                unescaped.append(JID_UNESCAPE_TRANSFORMATIONS.get(seq, char))

            # Pop character off the escape sequence, and ignore it
            seq = seq[1:]
        else:
            unescaped.append(char)
    unescaped = ''.join(unescaped)

    return unescaped


def _format_jid(local=None, domain=None, resource=None):
    """Format the given JID components into a full or bare JID.

    :param string local: Optional. The local portion of the JID.
    :param string domain: Required. The domain name portion of the JID.
    :param strin resource: Optional. The resource portion of the JID.

    :return: A full or bare JID string.
    """
    result = []
    if local:
        result.append(local)
        result.append('@')
    if domain:
        result.append(domain)
    if resource:
        result.append('/')
        result.append(resource)
    return ''.join(result)


class InvalidJID(ValueError):
    """
    Raised when attempting to create a JID that does not pass validation.

    It can also be raised if modifying an existing JID in such a way as
    to make it invalid, such trying to remove the domain from an existing
    full JID while the local and resource portions still exist.
    """

# pylint: disable=R0903
class UnescapedJID(object):

    """
    .. versionadded:: 1.1.10
    """

    def __init__(self, local, domain, resource):
        self._jid = (local, domain, resource)

    # pylint: disable=R0911
    def __getattr__(self, name):
        """Retrieve the given JID component.

        :param name: one of: user, server, domain, resource,
                     full, or bare.
        """
        if name == 'resource':
            return self._jid[2] or ''
        elif name in ('user', 'username', 'local', 'node'):
            return self._jid[0] or ''
        elif name in ('server', 'domain', 'host'):
            return self._jid[1] or ''
        elif name in ('full', 'jid'):
            return _format_jid(*self._jid)
        elif name == 'bare':
            return _format_jid(self._jid[0], self._jid[1])
        elif name == '_jid':
            return getattr(super(JID, self), '_jid')
        else:
            return None

    def __str__(self):
        """Use the full JID as the string value."""
        return _format_jid(*self._jid)

    def __repr__(self):
        """Use the full JID as the representation."""
        return self.__str__()


class JID(object):

    """
    A representation of a Jabber ID, or JID.

    Each JID may have three components: a user, a domain, and an optional
    resource. For example: user@domain/resource

    When a resource is not used, the JID is called a bare JID.
    The JID is a full JID otherwise.

    **JID Properties:**
        :jid: Alias for ``full``.
        :full: The string value of the full JID.
        :bare: The string value of the bare JID.
        :user: The username portion of the JID.
        :username: Alias for ``user``.
        :local: Alias for ``user``.
        :node: Alias for ``user``.
        :domain: The domain name portion of the JID.
        :server: Alias for ``domain``.
        :host: Alias for ``domain``.
        :resource: The resource portion of the JID.

    :param string jid:
        A string of the form ``'[user@]domain[/resource]'``.
    :param string local:
        Optional. Specify the local, or username, portion
        of the JID. If provided, it will override the local
        value provided by the `jid` parameter. The given
        local value will also be escaped if necessary.
    :param string domain:
        Optional. Specify the domain of the JID. If
        provided, it will override the domain given by
        the `jid` parameter.
    :param string resource:
        Optional. Specify the resource value of the JID.
        If provided, it will override the domain given
        by the `jid` parameter.

    :raises InvalidJID:
    """

    # pylint: disable=W0212
    def __init__(self, jid=None, **kwargs):
        locked = kwargs.get('cache_lock', False)
        in_local = kwargs.get('local', None)
        in_domain = kwargs.get('domain', None)
        in_resource = kwargs.get('resource', None)
        parts = None
        if in_local or in_domain or in_resource:
            parts = (in_local, in_domain, in_resource)

        # only check cache if there is a jid string, or parts, not if there
        # are both
        self._jid = None
        key = None
        if (jid is not None) and (parts is None):
            if isinstance(jid, JID):
                # it's already good to go, and there are no additions
                self._jid = jid._jid
                return
            key = jid
            self._jid, locked = JID_CACHE.get(jid, (None, locked))
        elif jid is None and parts is not None:
            key = parts
            self._jid, locked = JID_CACHE.get(parts, (None, locked))
        if not self._jid:
            if not jid:
                parsed_jid = (None, None, None)
            elif not isinstance(jid, JID):
                parsed_jid = _parse_jid(jid)
            else:
                parsed_jid = jid._jid

            local, domain, resource = parsed_jid

            if 'local' in kwargs:
                local = _escape_node(in_local)
            if 'domain' in kwargs:
                domain = _validate_domain(in_domain)
            if 'resource' in kwargs:
                resource = _validate_resource(in_resource)

            self._jid = (local, domain, resource)
            if key:
                _cache(key, self._jid, locked)

    def unescape(self):
        """Return an unescaped JID object.

        Using an unescaped JID is preferred for displaying JIDs
        to humans, and they should NOT be used for any other
        purposes than for presentation.

        :return: :class:`UnescapedJID`

        .. versionadded:: 1.1.10
        """
        return UnescapedJID(_unescape_node(self._jid[0]),
                            self._jid[1],
                            self._jid[2])

    def regenerate(self):
        """No-op

        .. deprecated:: 1.1.10
        """
        pass

    def reset(self, data):
        """Start fresh from a new JID string.

        :param string data: A string of the form ``'[user@]domain[/resource]'``.

        .. deprecated:: 1.1.10
        """
        self._jid = JID(data)._jid

    # pylint: disable=R0911
    def __getattr__(self, name):
        """Retrieve the given JID component.

        :param name: one of: user, server, domain, resource,
                     full, or bare.
        """
        if name == 'resource':
            return self._jid[2] or ''
        elif name in ('user', 'username', 'local', 'node'):
            return self._jid[0] or ''
        elif name in ('server', 'domain', 'host'):
            return self._jid[1] or ''
        elif name in ('full', 'jid'):
            return _format_jid(*self._jid)
        elif name == 'bare':
            return _format_jid(self._jid[0], self._jid[1])
        elif name == '_jid':
            return getattr(super(JID, self), '_jid')
        else:
            return None

    # pylint: disable=W0212
    def __setattr__(self, name, value):
        """Update the given JID component.

        :param name: one of: ``user``, ``username``, ``local``,
                             ``node``, ``server``, ``domain``, ``host``,
                             ``resource``, ``full``, ``jid``, or ``bare``.
        :param value: The new string value of the JID component.
        """
        if name == '_jid':
            super(JID, self).__setattr__('_jid', value)
        elif name == 'resource':
            self._jid = JID(self, resource=value)._jid
        elif name in ('user', 'username', 'local', 'node'):
            self._jid = JID(self, local=value)._jid
        elif name in ('server', 'domain', 'host'):
            self._jid = JID(self, domain=value)._jid
        elif name in ('full', 'jid'):
            self._jid = JID(value)._jid
        elif name == 'bare':
            parsed = JID(value)._jid
            self._jid = (parsed[0], parsed[1], self._jid[2])

    def __str__(self):
        """Use the full JID as the string value."""
        return _format_jid(*self._jid)

    def __repr__(self):
        """Use the full JID as the representation."""
        return self.__str__()

    # pylint: disable=W0212
    def __eq__(self, other):
        """Two JIDs are equal if they have the same full JID value."""
        if isinstance(other, UnescapedJID):
            return False

        other = JID(other)
        return self._jid == other._jid

    # pylint: disable=W0212
    def __ne__(self, other):
        """Two JIDs are considered unequal if they are not equal."""
        return not self == other

    def __hash__(self):
        """Hash a JID based on the string version of its full JID."""
        return hash(self.__str__())

    def __copy__(self):
        """Generate a duplicate JID."""
        return JID(self)
