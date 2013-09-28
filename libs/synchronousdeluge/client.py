import os
import platform

from collections import defaultdict
from itertools import imap

from synchronousdeluge.exceptions import DelugeRPCError
from synchronousdeluge.protocol import DelugeRPCRequest, DelugeRPCResponse
from synchronousdeluge.transfer import DelugeTransfer

__all__ = ["DelugeClient"]


RPC_RESPONSE = 1
RPC_ERROR = 2
RPC_EVENT = 3


class DelugeClient(object):
    def __init__(self):
        """A deluge client session."""
        self.transfer = DelugeTransfer()
        self.modules = []
        self._request_counter = 0

    def _get_local_auth(self):
        auth_file = ""
        username = password = ""
        if platform.system() in ('Windows', 'Microsoft'):
            appDataPath = os.environ.get("APPDATA")
            if not appDataPath:
                import _winreg
                hkey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders")
                appDataReg = _winreg.QueryValueEx(hkey, "AppData")
                appDataPath = appDataReg[0]
                _winreg.CloseKey(hkey)

            auth_file = os.path.join(appDataPath, "deluge", "auth")
        else:
            from xdg.BaseDirectory import save_config_path
            try:
                auth_file = os.path.join(save_config_path("deluge"), "auth")
            except OSError, e:
                return username, password


        if os.path.exists(auth_file):
            for line in open(auth_file):
                if line.startswith("#"):
                    # This is a comment line
                    continue
                line = line.strip()
                try:
                    lsplit = line.split(":")
                except Exception, e:
                    continue

                if len(lsplit) == 2:
                    username, password = lsplit
                elif len(lsplit) == 3:
                    username, password, level = lsplit
                else:
                    continue

                if username == "localclient":
                    return (username, password)

        return ("", "")

    def _create_module_method(self, module, method):
        fullname = "{0}.{1}".format(module, method)

        def func(obj, *args, **kwargs):
            return self.remote_call(fullname, *args, **kwargs)

        func.__name__ = method

        return func

    def _introspect(self):
        self.modules = []

        methods = self.remote_call("daemon.get_method_list").get()
        methodmap = defaultdict(dict)
        splitter = lambda v: v.split(".")

        for module, method in imap(splitter, methods):
            methodmap[module][method] = self._create_module_method(module, method)

        for module, methods in methodmap.items():
            clsname = "DelugeModule{0}".format(module.capitalize())
            cls = type(clsname, (), methods)
            setattr(self, module, cls())
            self.modules.append(module)

    def remote_call(self, method, *args, **kwargs):
        req = DelugeRPCRequest(self._request_counter, method, *args, **kwargs)
        message = next(self.transfer.send_request(req))

        response = DelugeRPCResponse()

        if not isinstance(message, tuple):
            return

        if len(message) < 3:
            return

        message_type = message[0]

#        if message_type == RPC_EVENT:
#            event = message[1]
#            values = message[2]
#
#            if event in self._event_handlers:
#                for handler in self._event_handlers[event]:
#                    gevent.spawn(handler, *values)
#
#        elif message_type in (RPC_RESPONSE, RPC_ERROR):
        if message_type in (RPC_RESPONSE, RPC_ERROR):
            request_id = message[1]
            value = message[2]

            if request_id == self._request_counter :
                if message_type == RPC_RESPONSE:
                    response.set(value)
                elif message_type == RPC_ERROR:
                    err = DelugeRPCError(*value)
                    response.set_exception(err)

        self._request_counter += 1
        return response

    def connect(self, host="127.0.0.1", port=58846, username="", password=""):
        """Connects to a daemon process.

        :param host: str, the hostname of the daemon
        :param port: int, the port of the daemon
        :param username: str, the username to login with
        :param password: str, the password to login with
        """

        # Connect transport
        self.transfer.connect((host, port))

        # Attempt to fetch local auth info if needed
        if not username and host in ("127.0.0.1", "localhost"):
            username, password = self._get_local_auth()

        # Authenticate
        self.remote_call("daemon.login", username, password).get()

        # Introspect available methods
        self._introspect()

    @property
    def connected(self):
        return self.transfer.connected

    def disconnect(self):
        """Disconnects from the daemon."""
        self.transfer.disconnect()

