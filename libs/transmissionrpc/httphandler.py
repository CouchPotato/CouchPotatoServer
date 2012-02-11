# -*- coding: utf-8 -*-
# Copyright (c) 2011 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import sys, httplib, urllib2

from transmissionrpc.error import HTTPHandlerError

class HTTPHandler(object):
    """
    Prototype for HTTP handling.
    """
    def set_authentication(self, uri, login, password):
        """
        Transmission use basic authentication in earlier versions and digest
        authentication in later versions.

         * uri, the authentication realm URI.
         * login, the authentication login.
         * password, the authentication password.
        """
        raise NotImplementedError("Bad HTTPHandler, failed to implement set_authentication.")

    def request(self, url, query, headers, timeout):
        """
        Implement a HTTP POST request here.

         * url, The URL to request.
         * query, The query data to send. This is a JSON data string.
         * headers, a dictionary of headers to send.
         * timeout, requested request timeout in seconds.
        """
        raise NotImplementedError("Bad HTTPHandler, failed to implement request.")

class DefaultHTTPHandler(HTTPHandler):
    """
    The default HTTP handler provided with transmissionrpc.
    """
    def __init__(self):
        HTTPHandler.__init__(self)

    def set_authentication(self, uri, login, password):
        password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(realm=None, uri=uri, user=login, passwd=password)
        opener = urllib2.build_opener(
            urllib2.HTTPBasicAuthHandler(password_manager)
            , urllib2.HTTPDigestAuthHandler(password_manager)
            )
        urllib2.install_opener(opener)

    def request(self, url, query, headers, timeout):
        request = urllib2.Request(url, query, headers)
        try:
            if (sys.version_info[0] == 2 and sys.version_info[1] > 5) or sys.version_info[0] > 2:
                response = urllib2.urlopen(request, timeout=timeout)
            else:
                response = urllib2.urlopen(request)
        except urllib2.HTTPError, error:
            if error.fp is None:
                raise HTTPHandlerError(error.filename, error.code, error.msg, dict(error.hdrs))
            else:
                raise HTTPHandlerError(error.filename, error.code, error.msg, dict(error.hdrs), error.read())
        except urllib2.URLError, error:
            # urllib2.URLError documentation is horrendous!
            # Try to get the tuple arguments of URLError
            if hasattr(error.reason, 'args') and isinstance(error.reason.args, tuple) and len(error.reason.args) == 2:
                raise HTTPHandlerError(httpcode=error.reason.args[0], httpmsg=error.reason.args[1])
            else:
                raise HTTPHandlerError(httpmsg='urllib2.URLError: %s' % (error.reason))
        except httplib.BadStatusLine, error:
            raise HTTPHandlerError(httpmsg='httplib.BadStatusLine: %s' % (error.line))
        return response.read()
