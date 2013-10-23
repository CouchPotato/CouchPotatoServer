"""
    sleekxmpp.xmlstream.xmlstream
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module provides the module for creating and
    interacting with generic XML streams, along with
    the necessary eventing infrastructure.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

from __future__ import with_statement, unicode_literals

import base64
import copy
import logging
import signal
import socket as Socket
import ssl
import sys
import threading
import time
import random
import weakref
import uuid

from xml.parsers.expat import ExpatError

import sleekxmpp
from sleekxmpp.util import Queue, QueueEmpty
from sleekxmpp.thirdparty.statemachine import StateMachine
from sleekxmpp.xmlstream import Scheduler, tostring, cert
from sleekxmpp.xmlstream.stanzabase import StanzaBase, ET, ElementBase
from sleekxmpp.xmlstream.handler import Waiter, XMLCallback
from sleekxmpp.xmlstream.matcher import MatchXMLMask
from sleekxmpp.xmlstream.resolver import resolve, default_resolver

# In Python 2.x, file socket objects are broken. A patched socket
# wrapper is provided for this case in filesocket.py.
if sys.version_info < (3, 0):
    from sleekxmpp.xmlstream.filesocket import FileSocket, Socket26


#: The time in seconds to wait before timing out waiting for response stanzas.
RESPONSE_TIMEOUT = 30

#: The time in seconds to wait for events from the event queue, and also the
#: time between checks for the process stop signal.
WAIT_TIMEOUT = 0.1

#: The number of threads to use to handle XML stream events. This is not the
#: same as the number of custom event handling threads.
#: :data:`HANDLER_THREADS` must be at least 1. For Python implementations
#: with a GIL, this should be left at 1, but for implemetnations without
#: a GIL increasing this value can provide better performance.
HANDLER_THREADS = 1

#: The time in seconds to delay between attempts to resend data
#: after an SSL error.
SSL_RETRY_DELAY = 0.5

#: The maximum number of times to attempt resending data due to
#: an SSL error.
SSL_RETRY_MAX = 10

#: Maximum time to delay between connection attempts is one hour.
RECONNECT_MAX_DELAY = 600

#: Maximum number of attempts to connect to the server before quitting
#: and raising a 'connect_failed' event. Setting this to ``None`` will
#: allow infinite reconnection attempts, and using ``0`` will disable
#: reconnections. Defaults to ``None``.
RECONNECT_MAX_ATTEMPTS = None


log = logging.getLogger(__name__)


class RestartStream(Exception):
    """
    Exception to restart stream processing, including
    resending the stream header.
    """


class XMLStream(object):
    """
    An XML stream connection manager and event dispatcher.

    The XMLStream class abstracts away the issues of establishing a
    connection with a server and sending and receiving XML "stanzas".
    A stanza is a complete XML element that is a direct child of a root
    document element. Two streams are used, one for each communication
    direction, over the same socket. Once the connection is closed, both
    streams should be complete and valid XML documents.

    Three types of events are provided to manage the stream:
        :Stream: Triggered based on received stanzas, similar in concept
                 to events in a SAX XML parser.
        :Custom: Triggered manually.
        :Scheduled: Triggered based on time delays.

    Typically, stanzas are first processed by a stream event handler which
    will then trigger custom events to continue further processing,
    especially since custom event handlers may run in individual threads.

    :param socket: Use an existing socket for the stream. Defaults to
                   ``None`` to generate a new socket.
    :param string host: The name of the target server.
    :param int port: The port to use for the connection. Defaults to 0.
    """

    def __init__(self, socket=None, host='', port=0):
        #: Most XMPP servers support TLSv1, but OpenFire in particular
        #: does not work well with it. For OpenFire, set
        #: :attr:`ssl_version` to use ``SSLv23``::
        #:
        #:     import ssl
        #:     xmpp.ssl_version = ssl.PROTOCOL_SSLv23
        self.ssl_version = ssl.PROTOCOL_TLSv1

        #: Path to a file containing certificates for verifying the
        #: server SSL certificate. A non-``None`` value will trigger
        #: certificate checking.
        #:
        #: .. note::
        #:
        #:     On Mac OS X, certificates in the system keyring will
        #:     be consulted, even if they are not in the provided file.
        self.ca_certs = None

        #: Path to a file containing a client certificate to use for
        #: authenticating via SASL EXTERNAL. If set, there must also
        #: be a corresponding `:attr:keyfile` value.
        self.certfile = None

        #: Path to a file containing the private key for the selected
        #: client certificate to use for authenticating via SASL EXTERNAL.
        self.keyfile = None

        self._der_cert = None

        #: The time in seconds to wait for events from the event queue,
        #: and also the time between checks for the process stop signal.
        self.wait_timeout = WAIT_TIMEOUT

        #: The time in seconds to wait before timing out waiting
        #: for response stanzas.
        self.response_timeout = RESPONSE_TIMEOUT

        #: The current amount to time to delay attempting to reconnect.
        #: This value doubles (with some jitter) with each failed
        #: connection attempt up to :attr:`reconnect_max_delay` seconds.
        self.reconnect_delay = None

        #: Maximum time to delay between connection attempts is one hour.
        self.reconnect_max_delay = RECONNECT_MAX_DELAY

        #: Maximum number of attempts to connect to the server before
        #: quitting and raising a 'connect_failed' event. Setting to
        #: ``None`` allows infinite reattempts, while setting it to ``0``
        #: will disable reconnection attempts. Defaults to ``None``.
        self.reconnect_max_attempts = RECONNECT_MAX_ATTEMPTS

        #: The time in seconds to delay between attempts to resend data
        #: after an SSL error.
        self.ssl_retry_max = SSL_RETRY_MAX

        #: The maximum number of times to attempt resending data due to
        #: an SSL error.
        self.ssl_retry_delay = SSL_RETRY_DELAY

        #: The connection state machine tracks if the stream is
        #: ``'connected'`` or ``'disconnected'``.
        self.state = StateMachine(('disconnected', 'connected'))
        self.state._set_state('disconnected')

        #: The default port to return when querying DNS records.
        self.default_port = int(port)

        #: The domain to try when querying DNS records.
        self.default_domain = ''

        #: The expected name of the server, for validation.
        self._expected_server_name = ''
        self._service_name = ''

        #: The desired, or actual, address of the connected server.
        self.address = (host, int(port))

        #: A file-like wrapper for the socket for use with the
        #: :mod:`~xml.etree.ElementTree` module.
        self.filesocket = None
        self.set_socket(socket)

        if sys.version_info < (3, 0):
            self.socket_class = Socket26
        else:
            self.socket_class = Socket.socket

        #: Enable connecting to the server directly over SSL, in
        #: particular when the service provides two ports: one for
        #: non-SSL traffic and another for SSL traffic.
        self.use_ssl = False

        #: Enable connecting to the service without using SSL
        #: immediately, but allow upgrading the connection later
        #: to use SSL.
        self.use_tls = False

        #: If set to ``True``, attempt to connect through an HTTP
        #: proxy based on the settings in :attr:`proxy_config`.
        self.use_proxy = False

        #: If set to ``True``, attempt to use IPv6.
        self.use_ipv6 = True

        #: Use CDATA for escaping instead of XML entities. Defaults
        #: to ``False``.
        self.use_cdata = False

        #: An optional dictionary of proxy settings. It may provide:
        #: :host: The host offering proxy services.
        #: :port: The port for the proxy service.
        #: :username: Optional username for accessing the proxy.
        #: :password: Optional password for accessing the proxy.
        self.proxy_config = {}

        #: The default namespace of the stream content, not of the
        #: stream wrapper itself.
        self.default_ns = ''

        self.default_lang = None
        self.peer_default_lang = None

        #: The namespace of the enveloping stream element.
        self.stream_ns = ''

        #: The default opening tag for the stream element.
        self.stream_header = "<stream>"

        #: The default closing tag for the stream element.
        self.stream_footer = "</stream>"

        #: If ``True``, periodically send a whitespace character over the
        #: wire to keep the connection alive. Mainly useful for connections
        #: traversing NAT.
        self.whitespace_keepalive = True

        #: The default interval between keepalive signals when
        #: :attr:`whitespace_keepalive` is enabled.
        self.whitespace_keepalive_interval = 300

        #: An :class:`~threading.Event` to signal that the application
        #: is stopping, and that all threads should shutdown.
        self.stop = threading.Event()

        #: An :class:`~threading.Event` to signal receiving a closing
        #: stream tag from the server.
        self.stream_end_event = threading.Event()
        self.stream_end_event.set()

        #: An :class:`~threading.Event` to signal the start of a stream
        #: session. Until this event fires, the send queue is not used
        #: and data is sent immediately over the wire.
        self.session_started_event = threading.Event()

        #: The default time in seconds to wait for a session to start
        #: after connecting before reconnecting and trying again.
        self.session_timeout = 45

        #: Flag for controlling if the session can be considered ended
        #: if the connection is terminated.
        self.end_session_on_disconnect = True

        #: A queue of stream, custom, and scheduled events to be processed.
        self.event_queue = Queue()

        #: A queue of string data to be sent over the stream.
        self.send_queue = Queue()
        self.send_queue_lock = threading.Lock()
        self.send_lock = threading.RLock()

        #: A :class:`~sleekxmpp.xmlstream.scheduler.Scheduler` instance for
        #: executing callbacks in the future based on time delays.
        self.scheduler = Scheduler(self.stop)
        self.__failed_send_stanza = None

        #: A mapping of XML namespaces to well-known prefixes.
        self.namespace_map = {StanzaBase.xml_ns: 'xml'}

        self.__thread = {}
        self.__root_stanza = []
        self.__handlers = []
        self.__event_handlers = {}
        self.__event_handlers_lock = threading.Lock()
        self.__filters = {'in': [], 'out': [], 'out_sync': []}
        self.__thread_count = 0
        self.__thread_cond = threading.Condition()
        self.__active_threads = set()
        self._use_daemons = False
        self._disconnect_wait_for_threads = True

        self._id = 0
        self._id_lock = threading.Lock()

        #: We use an ID prefix to ensure that all ID values are unique.
        self._id_prefix = '%s-' % uuid.uuid4()

        #: The :attr:`auto_reconnnect` setting controls whether or not
        #: the stream will be restarted in the event of an error.
        self.auto_reconnect = True

        #: The :attr:`disconnect_wait` setting is the default value
        #: for controlling if the system waits for the send queue to
        #: empty before ending the stream. This may be overridden by
        #: passing ``wait=True`` or ``wait=False`` to :meth:`disconnect`.
        #: The default :attr:`disconnect_wait` value is ``False``.
        self.disconnect_wait = False

        #: A list of DNS results that have not yet been tried.
        self.dns_answers = []

        #: The service name to check with DNS SRV records. For
        #: example, setting this to ``'xmpp-client'`` would query the
        #: ``_xmpp-client._tcp`` service.
        self.dns_service = None

        self.add_event_handler('connected', self._session_timeout_check)
        self.add_event_handler('disconnected', self._remove_schedules)
        self.add_event_handler('session_start', self._start_keepalive)
        self.add_event_handler('session_start', self._cert_expiration)

    def use_signals(self, signals=None):
        """Register signal handlers for ``SIGHUP`` and ``SIGTERM``.

        By using signals, a ``'killed'`` event will be raised when the
        application is terminated.

        If a signal handler already existed, it will be executed first,
        before the ``'killed'`` event is raised.

        :param list signals: A list of signal names to be monitored.
                             Defaults to ``['SIGHUP', 'SIGTERM']``.
        """
        if signals is None:
            signals = ['SIGHUP', 'SIGTERM']

        existing_handlers = {}
        for sig_name in signals:
            if hasattr(signal, sig_name):
                sig = getattr(signal, sig_name)
                handler = signal.getsignal(sig)
                if handler:
                    existing_handlers[sig] = handler

        def handle_kill(signum, frame):
            """
            Capture kill event and disconnect cleanly after first
            spawning the ``'killed'`` event.
            """

            if signum in existing_handlers and \
                   existing_handlers[signum] != handle_kill:
                existing_handlers[signum](signum, frame)

            self.event("killed", direct=True)
            self.disconnect()

        try:
            for sig_name in signals:
                if hasattr(signal, sig_name):
                    sig = getattr(signal, sig_name)
                    signal.signal(sig, handle_kill)
            self.__signals_installed = True
        except:
            log.debug("Can not set interrupt signal handlers. " + \
                      "SleekXMPP is not running from a main thread.")

    def new_id(self):
        """Generate and return a new stream ID in hexadecimal form.

        Many stanzas, handlers, or matchers may require unique
        ID values. Using this method ensures that all new ID values
        are unique in this stream.
        """
        with self._id_lock:
            self._id += 1
            return self.get_id()

    def get_id(self):
        """Return the current unique stream ID in hexadecimal form."""
        return "%s%X" % (self._id_prefix, self._id)

    def connect(self, host='', port=0, use_ssl=False,
                use_tls=True, reattempt=True):
        """Create a new socket and connect to the server.

        Setting ``reattempt`` to ``True`` will cause connection
        attempts to be made with an exponential backoff delay (max of
        :attr:`reconnect_max_delay` which defaults to 10 minute) until a
        successful connection is established.

        :param host: The name of the desired server for the connection.
        :param port: Port to connect to on the server.
        :param use_ssl: Flag indicating if SSL should be used by connecting
                        directly to a port using SSL.
        :param use_tls: Flag indicating if TLS should be used, allowing for
                        connecting to a port without using SSL immediately and
                        later upgrading the connection.
        :param reattempt: Flag indicating if the socket should reconnect
                          after disconnections.
        """
        self.stop.clear()

        if host and port:
            self.address = (host, int(port))
        try:
            Socket.inet_aton(self.address[0])
        except (Socket.error, ssl.SSLError):
            self.default_domain = self.address[0]

        # Respect previous SSL and TLS usage directives.
        if use_ssl is not None:
            self.use_ssl = use_ssl
        if use_tls is not None:
            self.use_tls = use_tls

        # Repeatedly attempt to connect until a successful connection
        # is established.
        attempts = self.reconnect_max_attempts
        connected = self.state.transition('disconnected', 'connected',
                                          func=self._connect,
                                          args=(reattempt,))
        while reattempt and not connected and not self.stop.is_set():
            connected = self.state.transition('disconnected', 'connected',
                                              func=self._connect)
            if not connected:
                if attempts is not None:
                    attempts -= 1
                    if attempts <= 0:
                        self.event('connection_failed', direct=True)
                        return False
        return connected

    def _connect(self, reattempt=True):
        self.scheduler.remove('Session timeout check')

        if self.reconnect_delay is None or not reattempt:
            delay = 1.0
        else:
            delay = min(self.reconnect_delay * 2, self.reconnect_max_delay)
            delay = random.normalvariate(delay, delay * 0.1)
            log.debug('Waiting %s seconds before connecting.', delay)
            elapsed = 0
            try:
                while elapsed < delay and not self.stop.is_set():
                    time.sleep(0.1)
                    elapsed += 0.1
            except KeyboardInterrupt:
                self.stop.set()
                return False
            except SystemExit:
                self.stop.set()
                return False

        if self.default_domain:
            try:
                host, address, port = self.pick_dns_answer(self.default_domain,
                                                           self.address[1])
                self.address = (address, port)
                self._service_name = host
            except StopIteration:
                log.debug("No remaining DNS records to try.")
                self.dns_answers = None
                if reattempt:
                    self.reconnect_delay = delay
                return False

        af = Socket.AF_INET
        proto = 'IPv4'
        if ':' in self.address[0]:
            af = Socket.AF_INET6
            proto = 'IPv6'
        try:
            self.socket = self.socket_class(af, Socket.SOCK_STREAM)
        except Socket.error:
            log.debug("Could not connect using %s", proto)
            return False

        self.configure_socket()

        if self.use_proxy:
            connected = self._connect_proxy()
            if not connected:
                if reattempt:
                    self.reconnect_delay = delay
                return False

        if self.use_ssl:
            log.debug("Socket Wrapped for SSL")
            if self.ca_certs is None:
                cert_policy = ssl.CERT_NONE
            else:
                cert_policy = ssl.CERT_REQUIRED

            ssl_socket = ssl.wrap_socket(self.socket,
                                         certfile=self.certfile,
                                         keyfile=self.keyfile,
                                         ca_certs=self.ca_certs,
                                         cert_reqs=cert_policy,
                                         do_handshake_on_connect=False)

            if hasattr(self.socket, 'socket'):
                # We are using a testing socket, so preserve the top
                # layer of wrapping.
                self.socket.socket = ssl_socket
            else:
                self.socket = ssl_socket

        try:
            if not self.use_proxy:
                domain = self.address[0]
                if ':' in domain:
                    domain = '[%s]' % domain
                log.debug("Connecting to %s:%s", domain, self.address[1])
                self.socket.connect(self.address)

                if self.use_ssl:
                    try:
                        self.socket.do_handshake()
                    except (Socket.error, ssl.SSLError):
                        log.error('CERT: Invalid certificate trust chain.')
                        if not self.event_handled('ssl_invalid_chain'):
                            self.disconnect(self.auto_reconnect,
                                            send_close=False)
                        else:
                            self.event('ssl_invalid_chain', direct=True)
                        return False

                    self._der_cert = self.socket.getpeercert(binary_form=True)
                    pem_cert = ssl.DER_cert_to_PEM_cert(self._der_cert)
                    log.debug('CERT: %s', pem_cert)

                    self.event('ssl_cert', pem_cert, direct=True)
                    try:
                        cert.verify(self._expected_server_name, self._der_cert)
                    except cert.CertificateError as err:
                        if not self.event_handled('ssl_invalid_cert'):
                            log.error(err.message)
                            self.disconnect(send_close=False)
                        else:
                            self.event('ssl_invalid_cert',
                                       pem_cert,
                                       direct=True)

            self.set_socket(self.socket, ignore=True)
            #this event is where you should set your application state
            self.event("connected", direct=True)
            self.reconnect_delay = 1.0
            return True
        except (Socket.error, ssl.SSLError) as serr:
            error_msg = "Could not connect to %s:%s. Socket Error #%s: %s"
            self.event('socket_error', serr, direct=True)
            domain = self.address[0]
            if ':' in domain:
                domain = '[%s]' % domain
            log.error(error_msg, domain, self.address[1],
                                 serr.errno, serr.strerror)
            return False

    def _connect_proxy(self):
        """Attempt to connect using an HTTP Proxy."""

        # Extract the proxy address, and optional credentials
        address = (self.proxy_config['host'], int(self.proxy_config['port']))
        cred = None
        if self.proxy_config['username']:
            username = self.proxy_config['username']
            password = self.proxy_config['password']

            cred = '%s:%s' % (username, password)
            if sys.version_info < (3, 0):
                cred = bytes(cred)
            else:
                cred = bytes(cred, 'utf-8')
            cred = base64.b64encode(cred).decode('utf-8')

        # Build the HTTP headers for connecting to the XMPP server
        headers = ['CONNECT %s:%s HTTP/1.0' % self.address,
                   'Host: %s:%s' % self.address,
                   'Proxy-Connection: Keep-Alive',
                   'Pragma: no-cache',
                   'User-Agent: SleekXMPP/%s' % sleekxmpp.__version__]
        if cred:
            headers.append('Proxy-Authorization: Basic %s' % cred)
        headers = '\r\n'.join(headers) + '\r\n\r\n'

        try:
            log.debug("Connecting to proxy: %s:%s", address)
            self.socket.connect(address)
            self.send_raw(headers, now=True)
            resp = ''
            while '\r\n\r\n' not in resp and not self.stop.is_set():
                resp += self.socket.recv(1024).decode('utf-8')
            log.debug('RECV: %s', resp)

            lines = resp.split('\r\n')
            if '200' not in lines[0]:
                self.event('proxy_error', resp)
                log.error('Proxy Error: %s', lines[0])
                return False

            # Proxy connection established, continue connecting
            # with the XMPP server.
            return True
        except (Socket.error, ssl.SSLError) as serr:
            error_msg = "Could not connect to %s:%s. Socket Error #%s: %s"
            self.event('socket_error', serr, direct=True)
            log.error(error_msg, self.address[0], self.address[1],
                                 serr.errno, serr.strerror)
            return False

    def _session_timeout_check(self, event=None):
        """
        Add check to ensure that a session is established within
        a reasonable amount of time.
        """

        def _handle_session_timeout():
            if not self.session_started_event.is_set():
                log.debug("Session start has taken more " + \
                          "than %d seconds", self.session_timeout)
                self.disconnect(reconnect=self.auto_reconnect)

        self.schedule("Session timeout check",
                self.session_timeout,
                _handle_session_timeout)

    def disconnect(self, reconnect=False, wait=None, send_close=True):
        """Terminate processing and close the XML streams.

        Optionally, the connection may be reconnected and
        resume processing afterwards.

        If the disconnect should take place after all items
        in the send queue have been sent, use ``wait=True``.

        .. warning::

            If you are constantly adding items to the queue
            such that it is never empty, then the disconnect will
            not occur and the call will continue to block.

        :param reconnect: Flag indicating if the connection
                          and processing should be restarted.
                          Defaults to ``False``.
        :param wait: Flag indicating if the send queue should
                     be emptied before disconnecting, overriding
                     :attr:`disconnect_wait`.
        :param send_close: Flag indicating if the stream footer
                           should be sent before terminating the
                           connection. Setting this to ``False``
                           prevents error loops when trying to
                           disconnect after a socket error.
        """
        self.state.transition('connected', 'disconnected',
                              wait=2.0,
                              func=self._disconnect,
                              args=(reconnect, wait, send_close))

    def _disconnect(self, reconnect=False, wait=None, send_close=True):
        if not reconnect:
            self.auto_reconnect = False

        if self.end_session_on_disconnect or send_close:
            self.event('session_end', direct=True)

        # Wait for the send queue to empty.
        if wait is not None:
            if wait:
                self.send_queue.join()
        elif self.disconnect_wait:
            self.send_queue.join()

        # Clearing this event will pause the send loop.
        self.session_started_event.clear()

        self.__failed_send_stanza = None

        # Send the end of stream marker.
        if send_close:
            self.send_raw(self.stream_footer, now=True)

        # Wait for confirmation that the stream was
        # closed in the other direction. If we didn't
        # send a stream footer we don't need to wait
        # since the server won't know to respond.
        if send_close:
            log.info('Waiting for %s from server', self.stream_footer)
            self.stream_end_event.wait(4)
        else:
            self.stream_end_event.set()

        if not self.auto_reconnect:
            self.stop.set()
            if self._disconnect_wait_for_threads:
                self._wait_for_threads()

        try:
            self.socket.shutdown(Socket.SHUT_RDWR)
            self.socket.close()
            self.filesocket.close()
        except (Socket.error, ssl.SSLError) as serr:
            self.event('socket_error', serr, direct=True)
        finally:
            #clear your application state
            self.event("disconnected", direct=True)
            return True

    def abort(self):
        self.session_started_event.clear()
        self.stop.set()
        if self._disconnect_wait_for_threads:
            self._wait_for_threads()
        try:
            self.socket.shutdown(Socket.SHUT_RDWR)
            self.socket.close()
            self.filesocket.close()
        except Socket.error:
            pass
        self.state.transition_any(['connected', 'disconnected'], 'disconnected', func=lambda: True)
        self.event("killed", direct=True)

    def reconnect(self, reattempt=True, wait=False, send_close=True):
        """Reset the stream's state and reconnect to the server."""
        log.debug("reconnecting...")
        if self.state.ensure('connected'):
            self.state.transition('connected', 'disconnected',
                    wait=2.0,
                    func=self._disconnect,
                    args=(True, wait, send_close))

        attempts = self.reconnect_max_attempts

        log.debug("connecting...")
        connected = self.state.transition('disconnected', 'connected',
                                          wait=2.0,
                                          func=self._connect,
                                          args=(reattempt,))
        while reattempt and not connected and not self.stop.is_set():
            connected = self.state.transition('disconnected', 'connected',
                                              wait=2.0, func=self._connect)
            connected = connected or self.state.ensure('connected')
            if not connected:
                if attempts is not None:
                    attempts -= 1
                    if attempts <= 0:
                        self.event('connection_failed', direct=True)
                        return False
        return connected

    def set_socket(self, socket, ignore=False):
        """Set the socket to use for the stream.

        The filesocket will be recreated as well.

        :param socket: The new socket object to use.
        :param bool ignore: If ``True``, don't set the connection
                            state to ``'connected'``.
        """
        self.socket = socket
        if socket is not None:
            # ElementTree.iterparse requires a file.
            # 0 buffer files have to be binary.

            # Use the correct fileobject type based on the Python
            # version to work around a broken implementation in
            # Python 2.x.
            if sys.version_info < (3, 0):
                self.filesocket = FileSocket(self.socket)
            else:
                self.filesocket = self.socket.makefile('rb', 0)
            if not ignore:
                self.state._set_state('connected')

    def configure_socket(self):
        """Set timeout and other options for self.socket.

        Meant to be overridden.
        """
        self.socket.settimeout(None)

    def configure_dns(self, resolver, domain=None, port=None):
        """
        Configure and set options for a :class:`~dns.resolver.Resolver`
        instance, and other DNS related tasks. For example, you
        can also check :meth:`~socket.socket.getaddrinfo` to see
        if you need to call out to ``libresolv.so.2`` to
        run ``res_init()``.

        Meant to be overridden.

        :param resolver: A :class:`~dns.resolver.Resolver` instance
                         or ``None`` if ``dnspython`` is not installed.
        :param domain: The initial domain under consideration.
        :param port: The initial port under consideration.
        """
        pass

    def start_tls(self):
        """Perform handshakes for TLS.

        If the handshake is successful, the XML stream will need
        to be restarted.
        """
        log.info("Negotiating TLS")
        log.info("Using SSL version: %s", str(self.ssl_version))
        if self.ca_certs is None:
            cert_policy = ssl.CERT_NONE
        else:
            cert_policy = ssl.CERT_REQUIRED

        ssl_socket = ssl.wrap_socket(self.socket,
                                     certfile=self.certfile,
                                     keyfile=self.keyfile,
                                     ssl_version=self.ssl_version,
                                     do_handshake_on_connect=False,
                                     ca_certs=self.ca_certs,
                                     cert_reqs=cert_policy)

        if hasattr(self.socket, 'socket'):
            # We are using a testing socket, so preserve the top
            # layer of wrapping.
            self.socket.socket = ssl_socket
        else:
            self.socket = ssl_socket

        try:
            self.socket.do_handshake()
        except (Socket.error, ssl.SSLError):
            log.error('CERT: Invalid certificate trust chain.')
            if not self.event_handled('ssl_invalid_chain'):
                self.disconnect(self.auto_reconnect, send_close=False)
            else:
                self._der_cert = self.socket.getpeercert(binary_form=True)
                self.event('ssl_invalid_chain', direct=True)
            return False

        self._der_cert = self.socket.getpeercert(binary_form=True)
        pem_cert = ssl.DER_cert_to_PEM_cert(self._der_cert)
        log.debug('CERT: %s', pem_cert)
        self.event('ssl_cert', pem_cert, direct=True)

        try:
            cert.verify(self._expected_server_name, self._der_cert)
        except cert.CertificateError as err:
            if not self.event_handled('ssl_invalid_cert'):
                log.error(err.message)
                self.disconnect(self.auto_reconnect, send_close=False)
            else:
                self.event('ssl_invalid_cert', pem_cert, direct=True)

        self.set_socket(self.socket)
        return True

    def _cert_expiration(self, event):
        """Schedule an event for when the TLS certificate expires."""

        if not self.use_tls and not self.use_ssl:
            return

        if not self._der_cert:
            log.warn("TLS or SSL was enabled, but no certificate was found.")
            return

        def restart():
            if not self.event_handled('ssl_expired_cert'):
                log.warn("The server certificate has expired. Restarting.")
                self.reconnect()
            else:
                pem_cert = ssl.DER_cert_to_PEM_cert(self._der_cert)
                self.event('ssl_expired_cert', pem_cert)

        cert_ttl = cert.get_ttl(self._der_cert)
        if cert_ttl is None:
            return

        if cert_ttl.days < 0:
            log.warn('CERT: Certificate has expired.')
            restart()

        try:
            total_seconds = cert_ttl.total_seconds()
        except AttributeError:
            # for Python < 2.7
            total_seconds = (cert_ttl.microseconds + (cert_ttl.seconds + cert_ttl.days * 24 * 3600) * 10**6) / 10**6

        log.info('CERT: Time until certificate expiration: %s' % cert_ttl)
        self.schedule('Certificate Expiration',
                      total_seconds,
                      restart)

    def _start_keepalive(self, event):
        """Begin sending whitespace periodically to keep the connection alive.

        May be disabled by setting::

            self.whitespace_keepalive = False

        The keepalive interval can be set using::

            self.whitespace_keepalive_interval = 300
        """
        self.schedule('Whitespace Keepalive',
                      self.whitespace_keepalive_interval,
                      self.send_raw,
                      args=(' ',),
                      kwargs={'now': True},
                      repeat=True)

    def _remove_schedules(self, event):
        """Remove whitespace keepalive and certificate expiration schedules."""
        self.scheduler.remove('Whitespace Keepalive')
        self.scheduler.remove('Certificate Expiration')

    def start_stream_handler(self, xml):
        """Perform any initialization actions, such as handshakes,
        once the stream header has been sent.

        Meant to be overridden.
        """
        pass

    def register_stanza(self, stanza_class):
        """Add a stanza object class as a known root stanza.

        A root stanza is one that appears as a direct child of the stream's
        root element.

        Stanzas that appear as substanzas of a root stanza do not need to
        be registered here. That is done using register_stanza_plugin() from
        sleekxmpp.xmlstream.stanzabase.

        Stanzas that are not registered will not be converted into
        stanza objects, but may still be processed using handlers and
        matchers.

        :param stanza_class: The top-level stanza object's class.
        """
        self.__root_stanza.append(stanza_class)

    def remove_stanza(self, stanza_class):
        """Remove a stanza from being a known root stanza.

        A root stanza is one that appears as a direct child of the stream's
        root element.

        Stanzas that are not registered will not be converted into
        stanza objects, but may still be processed using handlers and
        matchers.
        """
        self.__root_stanza.remove(stanza_class)

    def add_filter(self, mode, handler, order=None):
        """Add a filter for incoming or outgoing stanzas.

        These filters are applied before incoming stanzas are
        passed to any handlers, and before outgoing stanzas
        are put in the send queue.

        Each filter must accept a single stanza, and return
        either a stanza or ``None``. If the filter returns
        ``None``, then the stanza will be dropped from being
        processed for events or from being sent.

        :param mode: One of ``'in'`` or ``'out'``.
        :param handler: The filter function.
        :param int order: The position to insert the filter in
                          the list of active filters.
        """
        if order:
            self.__filters[mode].insert(order, handler)
        else:
            self.__filters[mode].append(handler)

    def del_filter(self, mode, handler):
        """Remove an incoming or outgoing filter."""
        self.__filters[mode].remove(handler)

    def add_handler(self, mask, pointer, name=None, disposable=False,
                    threaded=False, filter=False, instream=False):
        """A shortcut method for registering a handler using XML masks.

        The use of :meth:`register_handler()` is preferred.

        :param mask: An XML snippet matching the structure of the
                     stanzas that will be passed to this handler.
        :param pointer: The handler function itself.
        :parm name: A unique name for the handler. A name will
                    be generated if one is not provided.
        :param disposable: Indicates if the handler should be discarded
                           after one use.
        :param threaded: **DEPRECATED**.
                       Remains for backwards compatibility.
        :param filter: **DEPRECATED**.
                       Remains for backwards compatibility.
        :param instream: Indicates if the handler should execute during
                         stream processing and not during normal event
                         processing.
        """
        # To prevent circular dependencies, we must load the matcher
        # and handler classes here.

        if name is None:
            name = 'add_handler_%s' % self.getNewId()
        self.registerHandler(XMLCallback(name, MatchXMLMask(mask), pointer,
                                         once=disposable, instream=instream))

    def register_handler(self, handler, before=None, after=None):
        """Add a stream event handler that will be executed when a matching
        stanza is received.

        :param handler:
                The :class:`~sleekxmpp.xmlstream.handler.base.BaseHandler`
                derived object to execute.
        """
        if handler.stream is None:
            self.__handlers.append(handler)
            handler.stream = weakref.ref(self)

    def remove_handler(self, name):
        """Remove any stream event handlers with the given name.

        :param name: The name of the handler.
        """
        idx = 0
        for handler in self.__handlers:
            if handler.name == name:
                self.__handlers.pop(idx)
                return True
            idx += 1
        return False

    def get_dns_records(self, domain, port=None):
        """Get the DNS records for a domain.

        :param domain: The domain in question.
        :param port: If the results don't include a port, use this one.
        """
        if port is None:
            port = self.default_port

        resolver = default_resolver()
        self.configure_dns(resolver, domain=domain, port=port)

        return resolve(domain, port, service=self.dns_service,
                                     resolver=resolver,
                                     use_ipv6=self.use_ipv6)

    def pick_dns_answer(self, domain, port=None):
        """Pick a server and port from DNS answers.

        Gets DNS answers if none available.
        Removes used answer from available answers.

        :param domain: The domain in question.
        :param port: If the results don't include a port, use this one.
        """
        if not self.dns_answers:
            self.dns_answers = self.get_dns_records(domain, port)

        if sys.version_info < (3, 0):
            return self.dns_answers.next()
        else:
            return next(self.dns_answers)

    def add_event_handler(self, name, pointer,
                          threaded=False, disposable=False):
        """Add a custom event handler that will be executed whenever
        its event is manually triggered.

        :param name: The name of the event that will trigger
                     this handler.
        :param pointer: The function to execute.
        :param threaded: If set to ``True``, the handler will execute
                         in its own thread. Defaults to ``False``.
        :param disposable: If set to ``True``, the handler will be
                           discarded after one use. Defaults to ``False``.
        """
        if not name in self.__event_handlers:
            self.__event_handlers[name] = []
        self.__event_handlers[name].append((pointer, threaded, disposable))

    def del_event_handler(self, name, pointer):
        """Remove a function as a handler for an event.

        :param name: The name of the event.
        :param pointer: The function to remove as a handler.
        """
        if not name in self.__event_handlers:
            return

        # Need to keep handlers that do not use
        # the given function pointer
        def filter_pointers(handler):
            return handler[0] != pointer

        self.__event_handlers[name] = list(filter(
            filter_pointers,
            self.__event_handlers[name]))

    def event_handled(self, name):
        """Returns the number of registered handlers for an event.

        :param name: The name of the event to check.
        """
        return len(self.__event_handlers.get(name, []))

    def event(self, name, data={}, direct=False):
        """Manually trigger a custom event.

        :param name: The name of the event to trigger.
        :param data: Data that will be passed to each event handler.
                     Defaults to an empty dictionary, but is usually
                     a stanza object.
        :param direct: Runs the event directly if True, skipping the
                       event queue. All event handlers will run in the
                       same thread.
        """
        handlers = self.__event_handlers.get(name, [])
        for handler in handlers:
            #TODO:  Data should not be copied, but should be read only,
            #       but this might break current code so it's left for future.

            out_data = copy.copy(data) if len(handlers) > 1 else data
            old_exception = getattr(data, 'exception', None)
            if direct:
                try:
                    handler[0](out_data)
                except Exception as e:
                    error_msg = 'Error processing event handler: %s'
                    log.exception(error_msg,  str(handler[0]))
                    if old_exception:
                        old_exception(e)
                    else:
                        self.exception(e)
            else:
                self.event_queue.put(('event', handler, out_data))
            if handler[2]:
                # If the handler is disposable, we will go ahead and
                # remove it now instead of waiting for it to be
                # processed in the queue.
                with self.__event_handlers_lock:
                    try:
                        h_index = self.__event_handlers[name].index(handler)
                        self.__event_handlers[name].pop(h_index)
                    except:
                        pass

    def schedule(self, name, seconds, callback, args=None,
                 kwargs=None, repeat=False):
        """Schedule a callback function to execute after a given delay.

        :param name: A unique name for the scheduled callback.
        :param  seconds: The time in seconds to wait before executing.
        :param callback: A pointer to the function to execute.
        :param args: A tuple of arguments to pass to the function.
        :param kwargs: A dictionary of keyword arguments to pass to
                       the function.
        :param repeat: Flag indicating if the scheduled event should
                       be reset and repeat after executing.
        """
        self.scheduler.add(name, seconds, callback, args, kwargs,
                           repeat, qpointer=self.event_queue)

    def incoming_filter(self, xml):
        """Filter incoming XML objects before they are processed.

        Possible uses include remapping namespaces, or correcting elements
        from sources with incorrect behavior.

        Meant to be overridden.
        """
        return xml

    def send(self, data, mask=None, timeout=None, now=False, use_filters=True):
        """A wrapper for :meth:`send_raw()` for sending stanza objects.

        May optionally block until an expected response is received.

        :param data: The :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase`
                     stanza to send on the stream.
        :param mask: **DEPRECATED**
                     An XML string snippet matching the structure
                     of the expected response. Execution will block
                     in this thread until the response is received
                     or a timeout occurs.
        :param int timeout: Time in seconds to wait for a response before
                       continuing. Defaults to :attr:`response_timeout`.
        :param bool now: Indicates if the send queue should be skipped,
                        sending the stanza immediately. Useful mainly
                        for stream initialization stanzas.
                        Defaults to ``False``.
        :param bool use_filters: Indicates if outgoing filters should be
                                 applied to the given stanza data. Disabling
                                 filters is useful when resending stanzas.
                                 Defaults to ``True``.
        """
        if timeout is None:
            timeout = self.response_timeout
        if hasattr(mask, 'xml'):
            mask = mask.xml

        if isinstance(data, ElementBase):
            if use_filters:
                for filter in self.__filters['out']:
                    data = filter(data)
                    if data is None:
                        return

        if mask is not None:
            log.warning("Use of send mask waiters is deprecated.")
            wait_for = Waiter("SendWait_%s" % self.new_id(),
                              MatchXMLMask(mask))
            self.register_handler(wait_for)

        if isinstance(data, ElementBase):
            with self.send_queue_lock:
                if use_filters:
                    for filter in self.__filters['out_sync']:
                        data = filter(data)
                        if data is None:
                            return
                str_data = tostring(data.xml, xmlns=self.default_ns,
                                              stream=self,
                                              top_level=True)
                self.send_raw(str_data, now)
        else:
            self.send_raw(data, now)
        if mask is not None:
            return wait_for.wait(timeout)

    def send_xml(self, data, mask=None, timeout=None, now=False):
        """Send an XML object on the stream, and optionally wait
        for a response.

        :param data: The :class:`~xml.etree.ElementTree.Element` XML object
                     to send on the stream.
        :param mask: **DEPRECATED**
                     An XML string snippet matching the structure
                     of the expected response. Execution will block
                     in this thread until the response is received
                     or a timeout occurs.
        :param int timeout: Time in seconds to wait for a response before
                       continuing. Defaults to :attr:`response_timeout`.
        :param bool now: Indicates if the send queue should be skipped,
                        sending the stanza immediately. Useful mainly
                        for stream initialization stanzas.
                        Defaults to ``False``.
        """
        if timeout is None:
            timeout = self.response_timeout
        return self.send(tostring(data), mask, timeout, now)

    def send_raw(self, data, now=False, reconnect=None):
        """Send raw data across the stream.

        :param string data: Any string value.
        :param bool reconnect: Indicates if the stream should be
                               restarted if there is an error sending
                               the stanza. Used mainly for testing.
                               Defaults to :attr:`auto_reconnect`.
        """
        if now:
            log.debug("SEND (IMMED): %s", data)
            try:
                data = data.encode('utf-8')
                total = len(data)
                sent = 0
                count = 0
                tries = 0
                with self.send_lock:
                    while sent < total and not self.stop.is_set():
                        try:
                            sent += self.socket.send(data[sent:])
                            count += 1
                        except ssl.SSLError as serr:
                            if tries >= self.ssl_retry_max:
                                log.debug('SSL error: max retries reached')
                                self.exception(serr)
                                log.warning("Failed to send %s", data)
                                if reconnect is None:
                                    reconnect = self.auto_reconnect
                                if not self.stop.is_set():
                                    self.disconnect(reconnect,
                                                    send_close=False)
                                log.warning('SSL write error: retrying')
                            if not self.stop.is_set():
                                time.sleep(self.ssl_retry_delay)
                            tries += 1
                if count > 1:
                    log.debug('SENT: %d chunks', count)
            except (Socket.error, ssl.SSLError) as serr:
                self.event('socket_error', serr, direct=True)
                log.warning("Failed to send %s", data)
                if reconnect is None:
                    reconnect = self.auto_reconnect
                if not self.stop.is_set():
                    self.disconnect(reconnect, send_close=False)
        else:
            self.send_queue.put(data)
        return True

    def _start_thread(self, name, target, track=True):
        self.__active_threads.add(name)
        self.__thread[name] = threading.Thread(name=name, target=target)
        self.__thread[name].daemon = self._use_daemons
        self.__thread[name].start()

        if track:
            with self.__thread_cond:
                self.__thread_count += 1

    def _end_thread(self, name, early=False):
        with self.__thread_cond:
            curr_thread = threading.current_thread().name
            if curr_thread in self.__active_threads:
                self.__thread_count -= 1
                self.__active_threads.remove(curr_thread)

                if early:
                    log.debug('Threading deadlock prevention!')
                    log.debug(("Marked %s thread as ended due to " + \
                               "disconnect() call. %s threads remain.") % (
                                   name, self.__thread_count))
                else:
                    log.debug("Stopped %s thread. %s threads remain." % (
                        name, self.__thread_count))

            else:
                log.debug(("Finished exiting %s thread after early " + \
                           "termination from disconnect() call. " + \
                           "%s threads remain.") % (
                               name, self.__thread_count))

            if self.__thread_count == 0:
                self.__thread_cond.notify()

    def _wait_for_threads(self):
        with self.__thread_cond:
            if self.__thread_count != 0:
                log.debug("Waiting for %s threads to exit." %
                        self.__thread_count)
                name = threading.current_thread().name
                if name in self.__thread:
                    self._end_thread(name, early=True)
                self.__thread_cond.wait(4)
                if self.__thread_count != 0:
                    log.error("Hanged threads: %s" % threading.enumerate())
                    log.error("This may be due to calling disconnect() " + \
                              "from a non-threaded event handler. Be " + \
                              "sure that event handlers that call " + \
                              "disconnect() are registered using: " + \
                              "add_event_handler(..., threaded=True)")

    def process(self, **kwargs):
        """Initialize the XML streams and begin processing events.

        The number of threads used for processing stream events is determined
        by :data:`HANDLER_THREADS`.

        :param bool block: If ``False``, then event dispatcher will run
                    in a separate thread, allowing for the stream to be
                    used in the background for another application.
                    Otherwise, ``process(block=True)`` blocks the current
                    thread. Defaults to ``False``.
        :param bool threaded: **DEPRECATED**
                    If ``True``, then event dispatcher will run
                    in a separate thread, allowing for the stream to be
                    used in the background for another application.
                    Defaults to ``True``. This does **not** mean that no
                    threads are used at all if ``threaded=False``.

        Regardless of these threading options, these threads will
        always exist:

        - The event queue processor
        - The send queue processor
        - The scheduler
        """
        if 'threaded' in kwargs and 'block' in kwargs:
            raise ValueError("process() called with both " + \
                             "block and threaded arguments")
        elif 'block' in kwargs:
            threaded = not(kwargs.get('block', False))
        else:
            threaded = kwargs.get('threaded', True)

        for t in range(0, HANDLER_THREADS):
            log.debug("Starting HANDLER THREAD")
            self._start_thread('event_thread_%s' % t, self._event_runner)

        self._start_thread('send_thread', self._send_thread)
        self._start_thread('scheduler_thread', self._scheduler_thread)

        if threaded:
            # Run the XML stream in the background for another application.
            self._start_thread('read_thread', self._process, track=False)
        else:
            self._process()

    def _process(self):
        """Start processing the XML streams.

        Processing will continue after any recoverable errors
        if reconnections are allowed.
        """

        # The body of this loop will only execute once per connection.
        # Additional passes will be made only if an error occurs and
        # reconnecting is permitted.
        while True:
            shutdown = False
            try:
                # The call to self.__read_xml will block and prevent
                # the body of the loop from running until a disconnect
                # occurs. After any reconnection, the stream header will
                # be resent and processing will resume.
                while not self.stop.is_set():
                    # Only process the stream while connected to the server
                    if not self.state.ensure('connected', wait=0.1):
                        break
                    # Ensure the stream header is sent for any
                    # new connections.
                    if not self.session_started_event.is_set():
                        self.send_raw(self.stream_header, now=True)
                    if not self.__read_xml():
                        # If the server terminated the stream, end processing
                        break
            except KeyboardInterrupt:
                log.debug("Keyboard Escape Detected in _process")
                self.event('killed', direct=True)
                shutdown = True
            except SystemExit:
                log.debug("SystemExit in _process")
                shutdown = True
            except (SyntaxError, ExpatError) as e:
                log.error("Error reading from XML stream.")
                self.exception(e)
            except (Socket.error, ssl.SSLError) as serr:
                self.event('socket_error', serr, direct=True)
                log.error('Socket Error #%s: %s', serr.errno, serr.strerror)
            except ValueError as e:
                msg = e.message if hasattr(e, 'message') else e.args[0]

                if 'I/O operation on closed file' in msg:
                    log.error('Can not read from closed socket.')
                else:
                    self.exception(e)
            except Exception as e:
                if not self.stop.is_set():
                    log.error('Connection error.')
                self.exception(e)

            if not shutdown and not self.stop.is_set() \
               and self.auto_reconnect:
                self.reconnect()
            else:
                self.disconnect()
                break

    def __read_xml(self):
        """Parse the incoming XML stream

        Stream events are raised for each received stanza.
        """
        depth = 0
        root = None
        for event, xml in ET.iterparse(self.filesocket, (b'end', b'start')):
            if event == b'start':
                if depth == 0:
                    # We have received the start of the root element.
                    root = xml
                    log.debug('RECV: %s', tostring(root, xmlns=self.default_ns,
                                                         stream=self,
                                                         top_level=True,
                                                         open_only=True))
                    # Perform any stream initialization actions, such
                    # as handshakes.
                    self.stream_end_event.clear()
                    self.start_stream_handler(root)
                depth += 1
            if event == b'end':
                depth -= 1
                if depth == 0:
                    # The stream's root element has closed,
                    # terminating the stream.
                    log.debug("End of stream recieved")
                    self.stream_end_event.set()
                    return False
                elif depth == 1:
                    # We only raise events for stanzas that are direct
                    # children of the root element.
                    try:
                        self.__spawn_event(xml)
                    except RestartStream:
                        return True
                    if root is not None:
                        # Keep the root element empty of children to
                        # save on memory use.
                        root.clear()
        log.debug("Ending read XML loop")

    def _build_stanza(self, xml, default_ns=None):
        """Create a stanza object from a given XML object.

        If a specialized stanza type is not found for the XML, then
        a generic :class:`~sleekxmpp.xmlstream.stanzabase.StanzaBase`
        stanza will be returned.

        :param xml: The :class:`~xml.etree.ElementTree.Element` XML object
                    to convert into a stanza object.
        :param default_ns: Optional default namespace to use instead of the
                           stream's current default namespace.
        """
        if default_ns is None:
            default_ns = self.default_ns
        stanza_type = StanzaBase
        for stanza_class in self.__root_stanza:
            if xml.tag == "{%s}%s" % (default_ns, stanza_class.name) or \
               xml.tag == stanza_class.tag_name():
                stanza_type = stanza_class
                break
        stanza = stanza_type(self, xml)
        if stanza['lang'] is None and self.peer_default_lang:
            stanza['lang'] = self.peer_default_lang
        return stanza

    def __spawn_event(self, xml):
        """
        Analyze incoming XML stanzas and convert them into stanza
        objects if applicable and queue stream events to be processed
        by matching handlers.

        :param xml: The :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase`
                    stanza to analyze.
        """
        # Apply any preprocessing filters.
        xml = self.incoming_filter(xml)

        # Convert the raw XML object into a stanza object. If no registered
        # stanza type applies, a generic StanzaBase stanza will be used.
        stanza = self._build_stanza(xml)

        for filter in self.__filters['in']:
            if stanza is not None:
                stanza = filter(stanza)
        if stanza is None:
            return

        log.debug("RECV: %s", stanza)

        # Match the stanza against registered handlers. Handlers marked
        # to run "in stream" will be executed immediately; the rest will
        # be queued.
        unhandled = True
        matched_handlers = [h for h in self.__handlers if h.match(stanza)]
        for handler in matched_handlers:
            if len(matched_handlers) > 1:
                stanza_copy = copy.copy(stanza)
            else:
                stanza_copy = stanza
            handler.prerun(stanza_copy)
            self.event_queue.put(('stanza', handler, stanza_copy))
            try:
                if handler.check_delete():
                    self.__handlers.remove(handler)
            except:
                pass  # not thread safe
            unhandled = False

        # Some stanzas require responses, such as Iq queries. A default
        # handler will be executed immediately for this case.
        if unhandled:
            stanza.unhandled()

    def _threaded_event_wrapper(self, func, args):
        """Capture exceptions for event handlers that run
        in individual threads.

        :param func: The event handler to execute.
        :param args: Arguments to the event handler.
        """
        # this is always already copied before this is invoked
        orig = args[0]
        try:
            func(*args)
        except Exception as e:
            error_msg = 'Error processing event handler: %s'
            log.exception(error_msg, str(func))
            if hasattr(orig, 'exception'):
                orig.exception(e)
            else:
                self.exception(e)

    def _event_runner(self):
        """Process the event queue and execute handlers.

        The number of event runner threads is controlled by HANDLER_THREADS.

        Stream event handlers will all execute in this thread. Custom event
        handlers may be spawned in individual threads.
        """
        log.debug("Loading event runner")
        try:
            while not self.stop.is_set():
                try:
                    wait = self.wait_timeout
                    event = self.event_queue.get(True, timeout=wait)
                except QueueEmpty:
                    event = None
                if event is None:
                    continue

                etype, handler = event[0:2]
                args = event[2:]
                orig = copy.copy(args[0])

                if etype == 'stanza':
                    try:
                        handler.run(args[0])
                    except Exception as e:
                        error_msg = 'Error processing stream handler: %s'
                        log.exception(error_msg, handler.name)
                        orig.exception(e)
                elif etype == 'schedule':
                    name = args[1]
                    try:
                        log.debug('Scheduled event: %s: %s', name, args[0])
                        handler(*args[0])
                    except Exception as e:
                        log.exception('Error processing scheduled task')
                        self.exception(e)
                elif etype == 'event':
                    func, threaded, disposable = handler
                    try:
                        if threaded:
                            x = threading.Thread(
                                    name="Event_%s" % str(func),
                                    target=self._threaded_event_wrapper,
                                    args=(func, args))
                            x.daemon = self._use_daemons
                            x.start()
                        else:
                            func(*args)
                    except Exception as e:
                        error_msg = 'Error processing event handler: %s'
                        log.exception(error_msg, str(func))
                        if hasattr(orig, 'exception'):
                            orig.exception(e)
                        else:
                            self.exception(e)
                elif etype == 'quit':
                    log.debug("Quitting event runner thread")
                    break
        except KeyboardInterrupt:
            log.debug("Keyboard Escape Detected in _event_runner")
            self.event('killed', direct=True)
            self.disconnect()
        except SystemExit:
            self.disconnect()
            self.event_queue.put(('quit', None, None))

        self._end_thread('event runner')

    def _send_thread(self):
        """Extract stanzas from the send queue and send them on the stream."""
        try:
            while not self.stop.is_set():
                while not self.stop.is_set() and \
                      not self.session_started_event.is_set():
                    self.session_started_event.wait(timeout=0.1)
                if self.__failed_send_stanza is not None:
                    data = self.__failed_send_stanza
                    self.__failed_send_stanza = None
                else:
                    try:
                        data = self.send_queue.get(True, 1)
                    except QueueEmpty:
                        continue
                log.debug("SEND: %s", data)
                enc_data = data.encode('utf-8')
                total = len(enc_data)
                sent = 0
                count = 0
                tries = 0
                try:
                    with self.send_lock:
                        while sent < total and not self.stop.is_set() and \
                              self.session_started_event.is_set():
                            try:
                                sent += self.socket.send(enc_data[sent:])
                                count += 1
                            except ssl.SSLError as serr:
                                if tries >= self.ssl_retry_max:
                                    log.debug('SSL error: max retries reached')
                                    self.exception(serr)
                                    log.warning("Failed to send %s", data)
                                    if not self.stop.is_set():
                                        self.disconnect(self.auto_reconnect,
                                                        send_close=False)
                                    log.warning('SSL write error: retrying')
                                if not self.stop.is_set():
                                    time.sleep(self.ssl_retry_delay)
                                tries += 1
                    if count > 1:
                        log.debug('SENT: %d chunks', count)
                    self.send_queue.task_done()
                except (Socket.error, ssl.SSLError) as serr:
                    self.event('socket_error', serr, direct=True)
                    log.warning("Failed to send %s", data)
                    if not self.stop.is_set():
                        self.__failed_send_stanza = data
                        self._end_thread('send')
                        self.disconnect(self.auto_reconnect, send_close=False)
                        return
        except Exception as ex:
            log.exception('Unexpected error in send thread: %s', ex)
            self.exception(ex)
            if not self.stop.is_set():
                self._end_thread('send')
                self.disconnect(self.auto_reconnect)
                return

        self._end_thread('send')

    def _scheduler_thread(self):
        self.scheduler.process(threaded=False)
        self._end_thread('scheduler')

    def exception(self, exception):
        """Process an unknown exception.

        Meant to be overridden.

        :param exception: An unhandled exception object.
        """
        pass


# To comply with PEP8, method names now use underscores.
# Deprecated method names are re-mapped for backwards compatibility.
XMLStream.startTLS = XMLStream.start_tls
XMLStream.registerStanza = XMLStream.register_stanza
XMLStream.removeStanza = XMLStream.remove_stanza
XMLStream.registerHandler = XMLStream.register_handler
XMLStream.removeHandler = XMLStream.remove_handler
XMLStream.setSocket = XMLStream.set_socket
XMLStream.sendRaw = XMLStream.send_raw
XMLStream.getId = XMLStream.get_id
XMLStream.getNewId = XMLStream.new_id
XMLStream.sendXML = XMLStream.send_xml
