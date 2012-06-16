"""
oauthlib.utils
~~~~~~~~~~~~~~

This module contains utility methods used by various parts of the OAuth 2 spec.
"""

import random
import string
import time
import urllib
from urlparse import urlparse, urlunparse, parse_qsl

UNICODE_ASCII_CHARACTER_SET = (string.ascii_letters.decode('ascii') +
    string.digits.decode('ascii'))

def add_params_to_qs(query, params):
    """Extend a query with a list of two-tuples.

    :param query: Query string.
    :param params: List of two-tuples.
    :return: extended query
    """
    queryparams = parse_qsl(query, keep_blank_values=True)
    queryparams.extend(params)
    return urlencode(queryparams)


def add_params_to_uri(uri, params):
    """Add a list of two-tuples to the uri query components.

    :param uri: Full URI.
    :param params: List of two-tuples.
    :return: uri with extended query
    """
    sch, net, path, par, query, fra = urlparse(uri)
    query = add_params_to_qs(query, params)
    return urlunparse((sch, net, path, par, query, fra))


def escape(u):
    """Escape a string in an OAuth-compatible fashion.

    Per `section 3.6`_ of the spec.

    .. _`section 3.6`: http://tools.ietf.org/html/rfc5849#section-3.6

    """
    if not isinstance(u, unicode):
        raise ValueError('Only unicode objects are escapable.')
    return urllib.quote(u.encode('utf-8'), safe='~')


def generate_nonce():
    """Generate pseudorandom nonce that is unlikely to repeat.

    Per `section 3.2.1`_ of the MAC Access Authentication spec.

    A random 64-bit number is appended to the epoch timestamp for both
    randomness and to decrease the likelihood of collisions.

    .. _`section 3.2.1`: http://tools.ietf.org/html/draft-ietf-oauth-v2-http-mac-01#section-3.2.1
    """
    return unicode(unicode(random.getrandbits(64)) + generate_timestamp())


def generate_timestamp():
    """Get seconds since epoch (UTC).

    Per `section 3.2.1`_ of the MAC Access Authentication spec.

    .. _`section 3.2.1`: http://tools.ietf.org/html/draft-ietf-oauth-v2-http-mac-01#section-3.2.1
    """
    return unicode(int(time.time()))


def generate_token(length=20, chars=UNICODE_ASCII_CHARACTER_SET):
    """Generates a generic OAuth 2 token

    According to `section 1.4`_ and `section 1.5` of the spec, the method of token
    construction is undefined. This implementation is simply a random selection
    of `length` choices from `chars`. SystemRandom is used since it provides
    higher entropy than random.choice. 

    .. _`section 1.4`: http://tools.ietf.org/html/draft-ietf-oauth-v2-25#section-1.4
    .. _`section 1.5`: http://tools.ietf.org/html/draft-ietf-oauth-v2-25#section-1.5
    """
    rand = random.SystemRandom()
    return u''.join(rand.choice(chars) for x in range(length))


def host_from_uri(uri):
    """Extract hostname and port from URI.

    Will use default port for HTTP and HTTPS if none is present in the URI. 

    >>> host_from_uri(u'https://www.example.com/path?query')
    u'www.example.com', u'443'
    >>> host_from_uri(u'http://www.example.com:8080/path?query')
    u'www.example.com', u'8080'

    :param uri: Full URI.
    :param http_method: HTTP request method.
    :return: hostname, port
    """
    default_ports = {
        u'HTTP' : u'80',
        u'HTTPS' : u'443',
    }

    sch, netloc, path, par, query, fra = urlparse(uri)
    if u':' in netloc:
        netloc, port = netloc.split(u':', 1)
    else:
        port = default_ports.get(sch.upper())

    return netloc, port


def urlencode(query):
    """Encode a sequence of two-element tuples or dictionary into a URL query string.

    Operates using an OAuth-safe escape() method, in contrast to urllib.urlenocde.
    """
    # Convert dictionaries to list of tuples
    if isinstance(query, dict):
        query = query.items()
    return "&".join(['='.join([escape(k), escape(v)]) for k, v in query])
