
The ssl.match_hostname() function from Python 3.2
=================================================

The Secure Sockets layer is only actually *secure*
if you check the hostname in the certificate returned
by the server to which you are connecting,
and verify that it matches to hostname
that you are trying to reach.

But the matching logic, defined in `RFC2818`_,
can be a bit tricky to implement on your own.
So the ``ssl`` package in the Standard Library of Python 3.2
now includes a ``match_hostname()`` function
for performing this check instead of requiring every application
to implement the check separately.

This backport brings ``match_hostname()`` to users
of earlier versions of Python.
Simply make this distribution a dependency of your package,
and then use it like this::

    from backports.ssl_match_hostname import match_hostname, CertificateError
    ...
    sslsock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv3,
                              cert_reqs=ssl.CERT_REQUIRED, ca_certs=...)
    try:
        match_hostname(sslsock.getpeercert(), hostname)
    except CertificateError, ce:
        ...

Note that the ``ssl`` module is only included in the Standard Library
for Python 2.6 and later;
users of Python 2.5 or earlier versions
will also need to install the ``ssl`` distribution
from the Python Package Index to use code like that shown above.

Brandon Craig Rhodes is merely the packager of this distribution;
the actual code inside comes verbatim from Python 3.2.

.. _RFC2818: http://tools.ietf.org/html/rfc2818.html

