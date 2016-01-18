#
# Copyright (c) 2013 Dean Gardiner, <gardiner91@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from base64 import b64encode
import httplib
import xmlrpclib


class BasicAuthTransport(xmlrpclib.Transport):
    def __init__(self, secure=False, username=None, password=None):
        xmlrpclib.Transport.__init__(self)

        self.secure = secure

        self.username = username
        self.password = password

    def send_auth(self, h):
        if not self.username or not self.password:
            return

        auth = b64encode("%s:%s" % (self.username, self.password))

        h.putheader('Authorization', "Basic %s" % auth)

    def make_connection(self, host):
        if self._connection and host == self._connection[0]:
            return self._connection[1]

        chost, self._extra_headers, x509 = self.get_host_info(host)

        if self.secure:
            try:
                self._connection = host, httplib.HTTPSConnection(chost, None, **(x509 or {}))
            except AttributeError:
                raise NotImplementedError(
                    "your version of httplib doesn't support HTTPS"
                )
        else:
            self._connection = host, httplib.HTTPConnection(chost)

        return self._connection[1]


    def single_request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        try:
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_user_agent(h)
            self.send_auth(h)
            self.send_content(h, request_body)

            response = h.getresponse(buffering=True)
            if response.status == 200:
                self.verbose = verbose
                return self.parse_response(response)
        except xmlrpclib.Fault:
            raise
        except Exception:
            self.close()
            raise

        #discard any response data and raise exception
        if response.getheader("content-length", 0):
            response.read()
        raise xmlrpclib.ProtocolError(
            host + handler,
            response.status, response.reason,
            response.msg,
        )
