# -*- coding: utf-8 -*-

"""
requests.session
~~~~~~~~~~~~~~~~

This module provides a Session object to manage and persist settings across
requests (cookies, auth, proxies).

"""
import os
from collections import Mapping
from datetime import datetime

from .compat import cookielib, OrderedDict, urljoin, urlparse
from .cookies import cookiejar_from_dict, extract_cookies_to_jar, RequestsCookieJar
from .models import Request, PreparedRequest
from .hooks import default_hooks, dispatch_hook
from .utils import to_key_val_list, default_headers
from .exceptions import TooManyRedirects, InvalidSchema
from .structures import CaseInsensitiveDict

from .adapters import HTTPAdapter

from .utils import requote_uri, get_environ_proxies, get_netrc_auth

from .status_codes import codes
REDIRECT_STATI = (
    codes.moved, # 301
    codes.found, # 302
    codes.other, # 303
    codes.temporary_moved, # 307
)
DEFAULT_REDIRECT_LIMIT = 30


def merge_setting(request_setting, session_setting, dict_class=OrderedDict):
    """
    Determines appropriate setting for a given request, taking into account the
    explicit setting on that request, and the setting in the session. If a
    setting is a dictionary, they will be merged together using `dict_class`
    """

    if session_setting is None:
        return request_setting

    if request_setting is None:
        return session_setting

    # Bypass if not a dictionary (e.g. verify)
    if not (
            isinstance(session_setting, Mapping) and
            isinstance(request_setting, Mapping)
    ):
        return request_setting

    merged_setting = dict_class(to_key_val_list(session_setting))
    merged_setting.update(to_key_val_list(request_setting))

    # Remove keys that are set to None.
    for (k, v) in request_setting.items():
        if v is None:
            del merged_setting[k]

    return merged_setting


class SessionRedirectMixin(object):
    def resolve_redirects(self, resp, req, stream=False, timeout=None,
                          verify=True, cert=None, proxies=None):
        """Receives a Response. Returns a generator of Responses."""

        i = 0
        prepared_request = PreparedRequest()
        prepared_request.body = req.body
        prepared_request.headers = req.headers.copy()
        prepared_request.hooks = req.hooks
        prepared_request.method = req.method
        prepared_request.url = req.url

        # ((resp.status_code is codes.see_other))
        while (('location' in resp.headers and resp.status_code in REDIRECT_STATI)):

            resp.content  # Consume socket so it can be released

            if i >= self.max_redirects:
                raise TooManyRedirects('Exceeded %s redirects.' % self.max_redirects)

            # Release the connection back into the pool.
            resp.close()

            url = resp.headers['location']
            method = prepared_request.method

            # Handle redirection without scheme (see: RFC 1808 Section 4)
            if url.startswith('//'):
                parsed_rurl = urlparse(resp.url)
                url = '%s:%s' % (parsed_rurl.scheme, url)

            # Facilitate non-RFC2616-compliant 'location' headers
            # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
            # Compliant with RFC3986, we percent encode the url.
            if not urlparse(url).netloc:
                url = urljoin(resp.url, requote_uri(url))
            else:
                url = requote_uri(url)

            prepared_request.url = url

            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.4
            if (resp.status_code == codes.see_other and
                    prepared_request.method != 'HEAD'):
                method = 'GET'

            # Do what the browsers do, despite standards...
            if (resp.status_code in (codes.moved, codes.found) and
                    prepared_request.method not in ('GET', 'HEAD')):
                method = 'GET'

            prepared_request.method = method

            # https://github.com/kennethreitz/requests/issues/1084
            if resp.status_code not in (codes.temporary, codes.resume):
                if 'Content-Length' in prepared_request.headers:
                    del prepared_request.headers['Content-Length']

                prepared_request.body = None

            headers = prepared_request.headers
            try:
                del headers['Cookie']
            except KeyError:
                pass

            prepared_request.prepare_cookies(self.cookies)

            resp = self.send(
                prepared_request,
                stream=stream,
                timeout=timeout,
                verify=verify,
                cert=cert,
                proxies=proxies,
                allow_redirects=False,
            )

            extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)

            i += 1
            yield resp


class Session(SessionRedirectMixin):
    """A Requests session.

    Provides cookie persistience, connection-pooling, and configuration.

    Basic Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> s.get('http://httpbin.org/get')
      200
    """

    __attrs__ = [
        'headers', 'cookies', 'auth', 'timeout', 'proxies', 'hooks',
        'params', 'verify', 'cert', 'prefetch', 'adapters', 'stream',
        'trust_env', 'max_redirects']

    def __init__(self):

        #: A case-insensitive dictionary of headers to be sent on each
        #: :class:`Request <Request>` sent from this
        #: :class:`Session <Session>`.
        self.headers = default_headers()

        #: Default Authentication tuple or object to attach to
        #: :class:`Request <Request>`.
        self.auth = None

        #: Dictionary mapping protocol to the URL of the proxy (e.g.
        #: {'http': 'foo.bar:3128'}) to be used on each
        #: :class:`Request <Request>`.
        self.proxies = {}

        #: Event-handling hooks.
        self.hooks = default_hooks()

        #: Dictionary of querystring data to attach to each
        #: :class:`Request <Request>`. The dictionary values may be lists for
        #: representing multivalued query parameters.
        self.params = {}

        #: Stream response content default.
        self.stream = False

        #: SSL Verification default.
        self.verify = True

        #: SSL certificate default.
        self.cert = None

        #: Maximum number of redirects allowed. If the request exceeds this
        #: limit, a :class:`TooManyRedirects` exception is raised.
        self.max_redirects = DEFAULT_REDIRECT_LIMIT

        #: Should we trust the environment?
        self.trust_env = True

        # Set up a CookieJar to be used by default
        self.cookies = cookiejar_from_dict({})

        # Default connection adapters.
        self.adapters = OrderedDict()
        self.mount('https://', HTTPAdapter())
        self.mount('http://', HTTPAdapter())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def request(self, method, url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None):
        """Constructs a :class:`Request <Request>`, prepares it and sends it.
        Returns :class:`Response <Response>` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary or bytes to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of 'filename': file-like-objects
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) Float describing the timeout of the
            request.
        :param allow_redirects: (optional) Boolean. Set to True by default.
        :param proxies: (optional) Dictionary mapping protocol to the URL of
            the proxy.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) if ``True``, the SSL cert will be verified.
            A CA_BUNDLE path can also be provided.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair.
        """

        cookies = cookies or {}
        proxies = proxies or {}

        # Bootstrap CookieJar.
        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)

        # Merge with session cookies
        merged_cookies = RequestsCookieJar()
        merged_cookies.update(self.cookies)
        merged_cookies.update(cookies)
        cookies = merged_cookies

        # Gather clues from the surrounding environment.
        if self.trust_env:
            # Set environment's proxies.
            env_proxies = get_environ_proxies(url) or {}
            for (k, v) in env_proxies.items():
                proxies.setdefault(k, v)

            # Set environment's basic authentication.
            if not auth:
                auth = get_netrc_auth(url)

            # Look for configuration.
            if not verify and verify is not False:
                verify = os.environ.get('REQUESTS_CA_BUNDLE')

            # Curl compatibility.
            if not verify and verify is not False:
                verify = os.environ.get('CURL_CA_BUNDLE')

        # Merge all the kwargs.
        params = merge_setting(params, self.params)
        headers = merge_setting(headers, self.headers, dict_class=CaseInsensitiveDict)
        auth = merge_setting(auth, self.auth)
        proxies = merge_setting(proxies, self.proxies)
        hooks = merge_setting(hooks, self.hooks)
        stream = merge_setting(stream, self.stream)
        verify = merge_setting(verify, self.verify)
        cert = merge_setting(cert, self.cert)

        # Create the Request.
        req = Request()
        req.method = method.upper()
        req.url = url
        req.headers = headers
        req.files = files
        req.data = data
        req.params = params
        req.auth = auth
        req.cookies = cookies
        req.hooks = hooks

        # Prepare the Request.
        prep = req.prepare()

        # Send the request.
        send_kwargs = {
            'stream': stream,
            'timeout': timeout,
            'verify': verify,
            'cert': cert,
            'proxies': proxies,
            'allow_redirects': allow_redirects,
        }
        resp = self.send(prep, **send_kwargs)

        return resp

    def get(self, url, **kwargs):
        """Sends a GET request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        """

        kwargs.setdefault('allow_redirects', True)
        return self.request('GET', url, **kwargs)

    def options(self, url, **kwargs):
        """Sends a OPTIONS request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        """

        kwargs.setdefault('allow_redirects', True)
        return self.request('OPTIONS', url, **kwargs)

    def head(self, url, **kwargs):
        """Sends a HEAD request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        """

        kwargs.setdefault('allow_redirects', False)
        return self.request('HEAD', url, **kwargs)

    def post(self, url, data=None, **kwargs):
        """Sends a POST request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        """

        return self.request('POST', url, data=data, **kwargs)

    def put(self, url, data=None, **kwargs):
        """Sends a PUT request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        """

        return self.request('PUT', url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        """Sends a PATCH request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        """

        return self.request('PATCH', url,  data=data, **kwargs)

    def delete(self, url, **kwargs):
        """Sends a DELETE request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        """

        return self.request('DELETE', url, **kwargs)

    def send(self, request, **kwargs):
        """Send a given PreparedRequest."""
        # Set defaults that the hooks can utilize to ensure they always have
        # the correct parameters to reproduce the previous request.
        kwargs.setdefault('stream', self.stream)
        kwargs.setdefault('verify', self.verify)
        kwargs.setdefault('cert', self.cert)
        kwargs.setdefault('proxies', self.proxies)

        # It's possible that users might accidentally send a Request object.
        # Guard against that specific failure case.
        if getattr(request, 'prepare', None):
            raise ValueError('You can only send PreparedRequests.')

        # Set up variables needed for resolve_redirects and dispatching of
        # hooks
        allow_redirects = kwargs.pop('allow_redirects', True)
        stream = kwargs.get('stream')
        timeout = kwargs.get('timeout')
        verify = kwargs.get('verify')
        cert = kwargs.get('cert')
        proxies = kwargs.get('proxies')
        hooks = request.hooks

        # Get the appropriate adapter to use
        adapter = self.get_adapter(url=request.url)

        # Start time (approximately) of the request
        start = datetime.utcnow()
        # Send the request
        r = adapter.send(request, **kwargs)
        # Total elapsed time of the request (approximately)
        r.elapsed = datetime.utcnow() - start

        # Response manipulation hooks
        r = dispatch_hook('response', hooks, r, **kwargs)

        # Persist cookies
        extract_cookies_to_jar(self.cookies, request, r.raw)

        # Redirect resolving generator.
        gen = self.resolve_redirects(r, request, stream=stream,
                                     timeout=timeout, verify=verify, cert=cert,
                                     proxies=proxies)

        # Resolve redirects if allowed.
        history = [resp for resp in gen] if allow_redirects else []

        # Shuffle things around if there's history.
        if history:
            # Insert the first (original) request at the start
            history.insert(0, r)
            # Get the last request made
            r = history.pop()
            r.history = tuple(history)

        return r

    def get_adapter(self, url):
        """Returns the appropriate connnection adapter for the given URL."""
        for (prefix, adapter) in self.adapters.items():

            if url.startswith(prefix):
                return adapter

        # Nothing matches :-/
        raise InvalidSchema("No connection adapters were found for '%s'" % url)

    def close(self):
        """Closes all adapters and as such the session"""
        for _, v in self.adapters.items():
            v.close()

    def mount(self, prefix, adapter):
        """Registers a connection adapter to a prefix.

        Adapters are sorted in descending order by key length."""
        self.adapters[prefix] = adapter
        keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]
        for key in keys_to_move:
            self.adapters[key] = self.adapters.pop(key)

    def __getstate__(self):
        return dict((attr, getattr(self, attr, None)) for attr in self.__attrs__)

    def __setstate__(self, state):
        for attr, value in state.items():
            setattr(self, attr, value)


def session():
    """Returns a :class:`Session` for context-management."""

    return Session()
