import logging
import socket
import ssl
import struct
import warnings
import zlib

from .rencode import dumps, loads

RPC_RESPONSE = 1
RPC_ERROR = 2
RPC_EVENT = 3

MESSAGE_HEADER_SIZE = 5
READ_SIZE = 10

logger = logging.getLogger(__name__)


class DelugeClientException(Exception):
    """Base exception for all deluge client exceptions"""


class ConnectionLostException(DelugeClientException):
    pass


class CallTimeoutException(DelugeClientException):
    pass


class InvalidHeaderException(DelugeClientException):
    pass


class FailedToReconnectException(DelugeClientException):
    pass


class RemoteException(DelugeClientException):
    pass


class DelugeRPCClient(object):
    timeout = 20

    def __init__(self, host, port, username, password, decode_utf8=False, automatic_reconnect=True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.deluge_version = None
        # This is only applicable if deluge_version is 2
        self.deluge_protocol_version = None

        self.decode_utf8 = decode_utf8
        if not self.decode_utf8:
            warnings.warn('Using `decode_utf8=False` is deprecated, please set it to True.'
                          'The argument will be removed in a future release where it will be always True', DeprecationWarning)

        self.automatic_reconnect = automatic_reconnect

        self.request_id = 1
        self.connected = False
        self._create_socket()

    def _create_socket(self, ssl_version=None):
        if ssl_version is not None:
            self._socket = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), ssl_version=ssl_version)
        else:
            self._socket = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self._socket.settimeout(self.timeout)

    def connect(self):
        """
        Connects to the Deluge instance
        """
        self._connect()
        logger.debug('Connected to Deluge, detecting daemon version')
        self._detect_deluge_version()
        logger.debug('Daemon version {} detected, logging in'.format(self.deluge_version))
        if self.deluge_version == 2:
            result = self.call('daemon.login', self.username, self.password, client_version='deluge-client')
        else:
            result = self.call('daemon.login', self.username, self.password)
        logger.debug('Logged in with value %r' % result)
        self.connected = True

    def _connect(self):
        logger.info('Connecting to %s:%s' % (self.host, self.port))
        try:
            self._socket.connect((self.host, self.port))
        except ssl.SSLError as e:
            # Note: have not verified that we actually get errno 258 for this error
            if (hasattr(ssl, 'PROTOCOL_SSLv3') and
                    (getattr(e, 'reason', None) == 'UNSUPPORTED_PROTOCOL' or e.errno == 258)):
                logger.warning('Was unable to ssl handshake, trying to force SSLv3 (insecure)')
                self._create_socket(ssl_version=ssl.PROTOCOL_SSLv3)
                self._socket.connect((self.host, self.port))
            else:
                raise

    def disconnect(self):
        """
        Disconnect from deluge
        """
        if self.connected:
            self._socket.close()
            self._socket = None
            self.connected = False

    def _detect_deluge_version(self):
        if self.deluge_version is not None:
            return

        self._send_call(1, None, 'daemon.info')
        self._send_call(2, None, 'daemon.info')
        self._send_call(2, 1, 'daemon.info')
        result = self._socket.recv(1)
        if result[:1] == b'D':
            # This is a protocol deluge 2.0 was using before release
            self.deluge_version = 2
            self.deluge_protocol_version = None
            # If we need the specific version of deluge 2, this is it.
            daemon_version = self._receive_response(2, None, partial_data=result)
        elif ord(result[:1]) == 1:
            self.deluge_version = 2
            self.deluge_protocol_version = 1
            # If we need the specific version of deluge 2, this is it.
            daemon_version = self._receive_response(2, 1, partial_data=result)
        else:
            self.deluge_version = 1
            # Deluge 1 doesn't recover well from the bad request. Re-connect the socket.
            self._socket.close()
            self._create_socket()
            self._connect()

    def _send_call(self, deluge_version, protocol_version, method, *args, **kwargs):
        self.request_id += 1
        if method == 'daemon.login':
            debug_args = list(args)
            if len(debug_args) >= 2:
                debug_args[1] = '<password hidden>'
            logger.debug('Calling reqid %s method %r with args:%r kwargs:%r' % (self.request_id, method, debug_args, kwargs))
        else:
            logger.debug('Calling reqid %s method %r with args:%r kwargs:%r' % (self.request_id, method, args, kwargs))

        req = ((self.request_id, method, args, kwargs), )
        req = zlib.compress(dumps(req))

        if deluge_version == 2:
            if protocol_version is None:
                # This was a protocol for deluge 2 before they introduced protocol version numbers
                self._socket.send(b'D' + struct.pack("!i", len(req)))
            elif protocol_version == 1:
                self._socket.send(struct.pack('!BI', protocol_version, len(req)))
            else:
                raise Exception('Deluge protocol version {} is not (yet) supported.'.format(protocol_version))
        self._socket.send(req)

    def _receive_response(self, deluge_version, protocol_version, partial_data=b''):
        expected_bytes = None
        data = partial_data
        while True:
            try:
                d = self._socket.recv(READ_SIZE)
            except ssl.SSLError:
                raise CallTimeoutException()

            data += d
            if deluge_version == 2:
                if expected_bytes is None:
                    if len(data) < 5:
                        continue

                    header = data[:MESSAGE_HEADER_SIZE]
                    data = data[MESSAGE_HEADER_SIZE:]

                    if protocol_version is None:
                        if header[0] != b'D'[0]:
                            raise InvalidHeaderException('Expected D as first byte in reply')
                    elif ord(header[:1]) != protocol_version:
                        raise InvalidHeaderException(
                            'Expected protocol version ({}) as first byte in reply'.format(protocol_version)
                        )

                    if protocol_version is None:
                        expected_bytes = struct.unpack('!i', header[1:])[0]
                    else:
                        expected_bytes = struct.unpack('!I', header[1:])[0]

                if len(data) >= expected_bytes:
                    data = zlib.decompress(data)
                    break
            else:
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    if not d:
                        raise ConnectionLostException()
                    continue
                break

        data = list(loads(data, decode_utf8=self.decode_utf8))
        msg_type = data.pop(0)
        request_id = data.pop(0)

        if msg_type == RPC_ERROR:
            if self.deluge_version == 2:
                exception_type, exception_msg, _, traceback = data
                # On deluge 2, exception arguments are sent as tuple
                if self.decode_utf8:
                    exception_msg = ', '.join(exception_msg)
                else:
                    exception_msg = b', '.join(exception_msg)
            else:
                exception_type, exception_msg, traceback = data[0]
            if self.decode_utf8:
                exception = type(str(exception_type), (RemoteException, ), {})
                exception_msg = '%s\n%s' % (exception_msg,
                                            traceback)
            else:
                exception = type(str(exception_type.decode('utf-8', 'ignore')), (RemoteException, ), {})
                exception_msg = '%s\n%s' % (exception_msg.decode('utf-8', 'ignore'),
                                            traceback.decode('utf-8', 'ignore'))
            raise exception(exception_msg)
        elif msg_type == RPC_RESPONSE:
            retval = data[0]
            return retval

    def reconnect(self):
        """
        Reconnect
        """
        self.disconnect()
        self._create_socket()
        self.connect()

    def call(self, method, *args, **kwargs):
        """
        Calls an RPC function
        """
        tried_reconnect = False
        for _ in range(2):
            try:
                self._send_call(self.deluge_version, self.deluge_protocol_version, method, *args, **kwargs)
                return self._receive_response(self.deluge_version, self.deluge_protocol_version)
            except (socket.error, ConnectionLostException, CallTimeoutException):
                if self.automatic_reconnect:
                    if tried_reconnect:
                        raise FailedToReconnectException()
                    else:
                        try:
                            self.reconnect()
                        except (socket.error, ConnectionLostException, CallTimeoutException):
                            raise FailedToReconnectException()

                    tried_reconnect = True
                else:
                    raise

    def __getattr__(self, item):
        return RPCCaller(self.call, item)


class RPCCaller(object):
    def __init__(self, caller, method=''):
        self.caller = caller
        self.method = method

    def __getattr__(self, item):
        return RPCCaller(self.caller, self.method+'.'+item)

    def __call__(self, *args, **kwargs):
        return self.caller(self.method, *args, **kwargs)
