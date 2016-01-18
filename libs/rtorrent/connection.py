import logging
import urllib

from rtorrent.common import convert_version_tuple_to_str, join_uri, update_uri
from rtorrent.lib.xmlrpc.clients.http import HTTPServerProxy
from rtorrent.lib.xmlrpc.clients.scgi import SCGIServerProxy
from rtorrent.lib.xmlrpc.transports.basic_auth import BasicAuthTransport

# Try import requests transport (optional)
try:
    from rtorrent.lib.xmlrpc.transports.requests_ import RequestsTransport
except ImportError:
    RequestsTransport = None

MIN_RTORRENT_VERSION = (0, 8, 1)
MIN_RTORRENT_VERSION_STR = convert_version_tuple_to_str(MIN_RTORRENT_VERSION)

log = logging.getLogger(__name__)


class Connection(object):
    def __init__(self, uri, auth=None, verify_ssl=True, sp=None, sp_kwargs=None):
        self.auth = auth
        self.verify_ssl = verify_ssl

        # Transform + Parse URI
        self.uri = self._transform_uri(uri)
        self.scheme = urllib.splittype(self.uri)[0]

        # Construct RPC Client
        self.sp = self._get_sp(self.scheme, sp)
        self.sp_kwargs = sp_kwargs or {}

        self._client = None
        self._client_version_tuple = ()
        self._rpc_methods = []

    @property
    def client(self):
        if self._client is None:
            # Construct new client
            self._client = self.connect()

        # Return client
        return self._client

    def connect(self):
        log.debug('Connecting to server: %r', self.uri)

        if self.auth:
            # Construct server proxy with authentication transport
            return self.sp(self.uri, transport=self._construct_transport(), **self.sp_kwargs)

        # Construct plain server proxy
        return self.sp(self.uri, **self.sp_kwargs)

    def test(self):
        try:
            self.verify()
        except:
            return False

        return True

    def verify(self):
        # check for rpc methods that should be available
        assert "system.client_version" in self._get_rpc_methods(), "Required RPC method not available."
        assert "system.library_version" in self._get_rpc_methods(), "Required RPC method not available."

        # minimum rTorrent version check
        assert self._meets_version_requirement() is True,\
            "Error: Minimum rTorrent version required is {0}".format(MIN_RTORRENT_VERSION_STR)

    #
    # Private methods
    #

    def _construct_transport(self):
        # Ensure "auth" parameter is valid
        if type(self.auth) is not tuple or len(self.auth) != 3:
            raise ValueError('Invalid "auth" parameter format')

        # Construct transport with authentication details
        method, _, _ = self.auth
        secure = self.scheme == 'https'

        log.debug('Constructing transport for scheme: %r, authentication method: %r', self.scheme, method)

        # Use requests transport (if available)
        if RequestsTransport and method in ['basic', 'digest']:
            return RequestsTransport(
                secure, self.auth,
                verify_ssl=self.verify_ssl
            )

        # Use basic authentication transport
        if method == 'basic':
            return BasicAuthTransport(secure, self.auth)

        # Unsupported authentication method
        if method == 'digest':
            raise Exception('Digest authentication requires the "requests" library')

        raise NotImplementedError('Unknown authentication method: %r' % method)

    def _get_client_version_tuple(self):
        if not self._client_version_tuple:
            if not hasattr(self, "client_version"):
                setattr(self, "client_version", self.client.system.client_version())

            rtver = getattr(self, "client_version")
            self._client_version_tuple = tuple([int(i) for i in rtver.split(".")])

        return self._client_version_tuple

    def _get_rpc_methods(self):
        """ Get list of raw RPC commands

        @return: raw RPC commands
        @rtype: list
        """

        return(self._rpc_methods or self._update_rpc_methods())

    @staticmethod
    def _get_sp(scheme, sp):
        if sp:
            return sp

        if scheme in ['http', 'https']:
            return HTTPServerProxy

        if scheme == 'scgi':
            return SCGIServerProxy

        raise NotImplementedError()

    def _meets_version_requirement(self):
        return self._get_client_version_tuple() >= MIN_RTORRENT_VERSION

    @staticmethod
    def _transform_uri(uri):
        scheme = urllib.splittype(uri)[0]

        if scheme == 'httprpc' or scheme.startswith('httprpc+'):
            # Try find HTTPRPC transport (token after '+' in 'httprpc+https'), otherwise assume HTTP
            transport = scheme[scheme.index('+') + 1:] if '+' in scheme else 'http'

            # Transform URI with new path and scheme
            uri = join_uri(uri, 'plugins/httprpc/action.php', construct=False)
            return update_uri(uri, scheme=transport)

        return uri

    def _update_rpc_methods(self):
        self._rpc_methods = self.client.system.listMethods()

        return self._rpc_methods
