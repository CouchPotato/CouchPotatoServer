"""Blocking and non-blocking HTTP client interfaces.

This module defines a common interface shared by two implementations,
`simple_httpclient` and `curl_httpclient`.  Applications may either
instantiate their chosen implementation class directly or use the
`AsyncHTTPClient` class from this module, which selects an implementation
that can be overridden with the `AsyncHTTPClient.configure` method.

The default implementation is `simple_httpclient`, and this is expected
to be suitable for most users' needs.  However, some applications may wish
to switch to `curl_httpclient` for reasons such as the following:

* `curl_httpclient` has some features not found in `simple_httpclient`,
  including support for HTTP proxies and the ability to use a specified
  network interface.

* `curl_httpclient` is more likely to be compatible with sites that are
  not-quite-compliant with the HTTP spec, or sites that use little-exercised
  features of HTTP.

* `simple_httpclient` only supports SSL on Python 2.6 and above.

* `curl_httpclient` is faster

* `curl_httpclient` was the default prior to Tornado 2.0.

Note that if you are using `curl_httpclient`, it is highly recommended that
you use a recent version of ``libcurl`` and ``pycurl``.  Currently the minimum
supported version is 7.18.2, and the recommended version is 7.21.1 or newer.
"""

from __future__ import absolute_import, division, with_statement

import calendar
import email.utils
import httplib
import time
import weakref

from tornado.escape import utf8
from tornado import httputil, stack_context
from tornado.ioloop import IOLoop
from tornado.util import Configurable


class HTTPClient(object):
    """A blocking HTTP client.

    This interface is provided for convenience and testing; most applications
    that are running an IOLoop will want to use `AsyncHTTPClient` instead.
    Typical usage looks like this::

        http_client = httpclient.HTTPClient()
        try:
            response = http_client.fetch("http://www.google.com/")
            print response.body
        except httpclient.HTTPError, e:
            print "Error:", e
    """
    def __init__(self, async_client_class=None, **kwargs):
        self._io_loop = IOLoop()
        if async_client_class is None:
            async_client_class = AsyncHTTPClient
        self._async_client = async_client_class(self._io_loop, **kwargs)
        self._response = None
        self._closed = False

    def __del__(self):
        self.close()

    def close(self):
        """Closes the HTTPClient, freeing any resources used."""
        if not self._closed:
            self._async_client.close()
            self._io_loop.close()
            self._closed = True

    def fetch(self, request, **kwargs):
        """Executes a request, returning an `HTTPResponse`.

        The request may be either a string URL or an `HTTPRequest` object.
        If it is a string, we construct an `HTTPRequest` using any additional
        kwargs: ``HTTPRequest(request, **kwargs)``

        If an error occurs during the fetch, we raise an `HTTPError`.
        """
        def callback(response):
            self._response = response
            self._io_loop.stop()
        self._async_client.fetch(request, callback, **kwargs)
        self._io_loop.start()
        response = self._response
        self._response = None
        response.rethrow()
        return response


class AsyncHTTPClient(Configurable):
    """An non-blocking HTTP client.

    Example usage::

        import ioloop

        def handle_request(response):
            if response.error:
                print "Error:", response.error
            else:
                print response.body
            ioloop.IOLoop.instance().stop()

        http_client = httpclient.AsyncHTTPClient()
        http_client.fetch("http://www.google.com/", handle_request)
        ioloop.IOLoop.instance().start()

    The constructor for this class is magic in several respects:  It actually
    creates an instance of an implementation-specific subclass, and instances
    are reused as a kind of pseudo-singleton (one per IOLoop).  The keyword
    argument force_instance=True can be used to suppress this singleton
    behavior.  Constructor arguments other than io_loop and force_instance
    are deprecated.  The implementation subclass as well as arguments to
    its constructor can be set with the static method configure()
    """
    @classmethod
    def configurable_base(cls):
        return AsyncHTTPClient

    @classmethod
    def configurable_default(cls):
        from tornado.simple_httpclient import SimpleAsyncHTTPClient
        return SimpleAsyncHTTPClient

    @classmethod
    def _async_clients(cls):
        attr_name = '_async_client_dict_' + cls.__name__
        if not hasattr(cls, attr_name):
            setattr(cls, attr_name,  weakref.WeakKeyDictionary())
        return getattr(cls, attr_name)

    def __new__(cls, io_loop=None, force_instance=False, **kwargs):
        io_loop = io_loop or IOLoop.instance()
        if io_loop in cls._async_clients() and not force_instance:
            return cls._async_clients()[io_loop]
        instance = super(AsyncHTTPClient, cls).__new__(cls, io_loop=io_loop,
                                                       **kwargs)
        if not force_instance:
            cls._async_clients()[io_loop] = instance
        return instance

    def close(self):
        """Destroys this http client, freeing any file descriptors used.
        Not needed in normal use, but may be helpful in unittests that
        create and destroy http clients.  No other methods may be called
        on the AsyncHTTPClient after close().
        """
        if self._async_clients().get(self.io_loop) is self:
            del self._async_clients()[self.io_loop]

    def fetch(self, request, callback, **kwargs):
        """Executes a request, calling callback with an `HTTPResponse`.

        The request may be either a string URL or an `HTTPRequest` object.
        If it is a string, we construct an `HTTPRequest` using any additional
        kwargs: ``HTTPRequest(request, **kwargs)``

        If an error occurs during the fetch, the HTTPResponse given to the
        callback has a non-None error attribute that contains the exception
        encountered during the request. You can call response.rethrow() to
        throw the exception (if any) in the callback.
        """
        raise NotImplementedError()

    @classmethod
    def configure(cls, impl, **kwargs):
        """Configures the AsyncHTTPClient subclass to use.

        AsyncHTTPClient() actually creates an instance of a subclass.
        This method may be called with either a class object or the
        fully-qualified name of such a class (or None to use the default,
        SimpleAsyncHTTPClient)

        If additional keyword arguments are given, they will be passed
        to the constructor of each subclass instance created.  The
        keyword argument max_clients determines the maximum number of
        simultaneous fetch() operations that can execute in parallel
        on each IOLoop.  Additional arguments may be supported depending
        on the implementation class in use.

        Example::

           AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        """
        super(AsyncHTTPClient, cls).configure(impl, **kwargs)


class HTTPRequest(object):
    """HTTP client request object."""

    # Default values for HTTPRequest parameters.
    # Merged with the values on the request object by AsyncHTTPClient
    # implementations.
    _DEFAULTS = dict(
        connect_timeout=20.0,
        request_timeout=20.0,
        follow_redirects=True,
        max_redirects=5,
        use_gzip=True,
        proxy_password='',
        allow_nonstandard_methods=False,
        validate_cert=True)

    def __init__(self, url, method="GET", headers=None, body=None,
                 auth_username=None, auth_password=None,
                 connect_timeout=None, request_timeout=None,
                 if_modified_since=None, follow_redirects=None,
                 max_redirects=None, user_agent=None, use_gzip=None,
                 network_interface=None, streaming_callback=None,
                 header_callback=None, prepare_curl_callback=None,
                 proxy_host=None, proxy_port=None, proxy_username=None,
                 proxy_password=None, allow_nonstandard_methods=None,
                 validate_cert=None, ca_certs=None,
                 allow_ipv6=None,
                 client_key=None, client_cert=None):
        r"""Creates an `HTTPRequest`.

        All parameters except `url` are optional.

        :arg string url: URL to fetch
        :arg string method: HTTP method, e.g. "GET" or "POST"
        :arg headers: Additional HTTP headers to pass on the request
        :type headers: `~tornado.httputil.HTTPHeaders` or `dict`
        :arg string auth_username: Username for HTTP "Basic" authentication
        :arg string auth_password: Password for HTTP "Basic" authentication
        :arg float connect_timeout: Timeout for initial connection in seconds
        :arg float request_timeout: Timeout for entire request in seconds
        :arg datetime if_modified_since: Timestamp for ``If-Modified-Since``
           header
        :arg bool follow_redirects: Should redirects be followed automatically
           or return the 3xx response?
        :arg int max_redirects: Limit for `follow_redirects`
        :arg string user_agent: String to send as ``User-Agent`` header
        :arg bool use_gzip: Request gzip encoding from the server
        :arg string network_interface: Network interface to use for request
        :arg callable streaming_callback: If set, `streaming_callback` will
           be run with each chunk of data as it is received, and
           `~HTTPResponse.body` and `~HTTPResponse.buffer` will be empty in
           the final response.
        :arg callable header_callback: If set, `header_callback` will
           be run with each header line as it is received (including the
           first line, e.g. ``HTTP/1.0 200 OK\r\n``, and a final line
           containing only ``\r\n``.  All lines include the trailing newline
           characters).  `~HTTPResponse.headers` will be empty in the final
           response.  This is most useful in conjunction with
           `streaming_callback`, because it's the only way to get access to
           header data while the request is in progress.
        :arg callable prepare_curl_callback: If set, will be called with
           a `pycurl.Curl` object to allow the application to make additional
           `setopt` calls.
        :arg string proxy_host: HTTP proxy hostname.  To use proxies,
           `proxy_host` and `proxy_port` must be set; `proxy_username` and
           `proxy_pass` are optional.  Proxies are currently only support
           with `curl_httpclient`.
        :arg int proxy_port: HTTP proxy port
        :arg string proxy_username: HTTP proxy username
        :arg string proxy_password: HTTP proxy password
        :arg bool allow_nonstandard_methods: Allow unknown values for `method`
           argument?
        :arg bool validate_cert: For HTTPS requests, validate the server's
           certificate?
        :arg string ca_certs: filename of CA certificates in PEM format,
           or None to use defaults.  Note that in `curl_httpclient`, if
           any request uses a custom `ca_certs` file, they all must (they
           don't have to all use the same `ca_certs`, but it's not possible
           to mix requests with ca_certs and requests that use the defaults.
        :arg bool allow_ipv6: Use IPv6 when available?  Default is false in
           `simple_httpclient` and true in `curl_httpclient`
        :arg string client_key: Filename for client SSL key, if any
        :arg string client_cert: Filename for client SSL certificate, if any
        """
        if headers is None:
            headers = httputil.HTTPHeaders()
        if if_modified_since:
            timestamp = calendar.timegm(if_modified_since.utctimetuple())
            headers["If-Modified-Since"] = email.utils.formatdate(
                timestamp, localtime=False, usegmt=True)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.url = url
        self.method = method
        self.headers = headers
        self.body = utf8(body)
        self.auth_username = auth_username
        self.auth_password = auth_password
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.user_agent = user_agent
        self.use_gzip = use_gzip
        self.network_interface = network_interface
        self.streaming_callback = stack_context.wrap(streaming_callback)
        self.header_callback = stack_context.wrap(header_callback)
        self.prepare_curl_callback = stack_context.wrap(prepare_curl_callback)
        self.allow_nonstandard_methods = allow_nonstandard_methods
        self.validate_cert = validate_cert
        self.ca_certs = ca_certs
        self.allow_ipv6 = allow_ipv6
        self.client_key = client_key
        self.client_cert = client_cert
        self.start_time = time.time()


class HTTPResponse(object):
    """HTTP Response object.

    Attributes:

    * request: HTTPRequest object

    * code: numeric HTTP status code, e.g. 200 or 404

    * reason: human-readable reason phrase describing the status code
        (with curl_httpclient, this is a default value rather than the
        server's actual response)

    * headers: httputil.HTTPHeaders object

    * buffer: cStringIO object for response body

    * body: response body as string (created on demand from self.buffer)

    * error: Exception object, if any

    * request_time: seconds from request start to finish

    * time_info: dictionary of diagnostic timing information from the request.
        Available data are subject to change, but currently uses timings
        available from http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html,
        plus 'queue', which is the delay (if any) introduced by waiting for
        a slot under AsyncHTTPClient's max_clients setting.
    """
    def __init__(self, request, code, headers=None, buffer=None,
                 effective_url=None, error=None, request_time=None,
                 time_info=None, reason=None):
        self.request = request
        self.code = code
        self.reason = reason or httplib.responses.get(code, "Unknown")
        if headers is not None:
            self.headers = headers
        else:
            self.headers = httputil.HTTPHeaders()
        self.buffer = buffer
        self._body = None
        if effective_url is None:
            self.effective_url = request.url
        else:
            self.effective_url = effective_url
        if error is None:
            if self.code < 200 or self.code >= 300:
                self.error = HTTPError(self.code, response=self)
            else:
                self.error = None
        else:
            self.error = error
        self.request_time = request_time
        self.time_info = time_info or {}

    def _get_body(self):
        if self.buffer is None:
            return None
        elif self._body is None:
            self._body = self.buffer.getvalue()

        return self._body

    body = property(_get_body)

    def rethrow(self):
        """If there was an error on the request, raise an `HTTPError`."""
        if self.error:
            raise self.error

    def __repr__(self):
        args = ",".join("%s=%r" % i for i in self.__dict__.iteritems())
        return "%s(%s)" % (self.__class__.__name__, args)


class HTTPError(Exception):
    """Exception thrown for an unsuccessful HTTP request.

    Attributes:

    code - HTTP error integer error code, e.g. 404.  Error code 599 is
           used when no HTTP response was received, e.g. for a timeout.

    response - HTTPResponse object, if any.

    Note that if follow_redirects is False, redirects become HTTPErrors,
    and you can look at error.response.headers['Location'] to see the
    destination of the redirect.
    """
    def __init__(self, code, message=None, response=None):
        self.code = code
        message = message or httplib.responses.get(code, "Unknown")
        self.response = response
        Exception.__init__(self, "HTTP %d: %s" % (self.code, message))

class _RequestProxy(object):
    """Combines an object with a dictionary of defaults.

    Used internally by AsyncHTTPClient implementations.
    """
    def __init__(self, request, defaults):
        self.request = request
        self.defaults = defaults

    def __getattr__(self, name):
        request_attr = getattr(self.request, name)
        if request_attr is not None:
            return request_attr
        elif self.defaults is not None:
            return self.defaults.get(name, None)
        else:
            return None


def main():
    from tornado.options import define, options, parse_command_line
    define("print_headers", type=bool, default=False)
    define("print_body", type=bool, default=True)
    define("follow_redirects", type=bool, default=True)
    define("validate_cert", type=bool, default=True)
    args = parse_command_line()
    client = HTTPClient()
    for arg in args:
        try:
            response = client.fetch(arg,
                                    follow_redirects=options.follow_redirects,
                                    validate_cert=options.validate_cert,
                                    )
        except HTTPError, e:
            if e.response is not None:
                response = e.response
            else:
                raise
        if options.print_headers:
            print response.headers
        if options.print_body:
            print response.body
    client.close()

if __name__ == "__main__":
    main()
