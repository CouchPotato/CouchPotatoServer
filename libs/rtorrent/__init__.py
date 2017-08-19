# Copyright (c) 2013 Chris Lucas, <chris@chrisjlucas.com>
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
import urllib
import os.path
import time
import xmlrpclib

from rtorrent.connection import Connection
from rtorrent.common import find_torrent, join_uri, \
    update_uri, is_valid_port, convert_version_tuple_to_str
from rtorrent.lib.torrentparser import TorrentParser
from rtorrent.rpc import Method
from rtorrent.torrent import Torrent
from rtorrent.group import Group
import rtorrent.rpc  # @UnresolvedImport

__version__ = "0.2.9"
__author__ = "Chris Lucas"
__contact__ = "chris@chrisjlucas.com"
__license__ = "MIT"


class RTorrent:
    """ Create a new rTorrent connection """
    rpc_prefix = None

    def __init__(self, uri, auth=None, verify_server=False, verify_ssl=True, sp=None, sp_kwargs=None):

        self.connection = Connection(uri, auth, verify_ssl, sp, sp_kwargs)
        self.torrents = []  # : List of L{Torrent} instances

        self._torrent_cache = []

        # Verify connection is valid
        if verify_server is True:
            self.connection.verify()

    @property
    def client(self):
        return self.connection.client

    def _get_conn(self):
        return self.client

    def get_torrents(self, view="main"):
        """Get list of all torrents in specified view

        @return: list of L{Torrent} instances

        @rtype: list

        @todo: add validity check for specified view
        """
        self.torrents = []
        methods = rtorrent.torrent.methods
        retriever_methods = [m for m in methods
                             if m.is_retriever() and m.is_available(self)]

        m = rtorrent.rpc.Multicall(self)
        # multicall2 wants .. something .. as its first argument. It accepts a blank string, so let's go with that.
        MCFirstArg = ""
        m.add("d.multicall2", MCFirstArg, view, "d.hash=",
              *[method.rpc_call + "=" for method in retriever_methods])

        results = m.call()[0]  # only sent one call, only need first result

        for result in results:
            results_dict = {}
            # build results_dict
            for m, r in zip(retriever_methods, result[1:]):  # result[0] is the info_hash
                results_dict[m.varname] = rtorrent.rpc.process_result(m, r)

            self.torrents.append(
                Torrent(self, info_hash=result[0], **results_dict)
            )

        self._manage_torrent_cache()
        return(self.torrents)

    def _manage_torrent_cache(self):
        """Carry tracker/peer/file lists over to new torrent list"""
        for torrent in self._torrent_cache:
            new_torrent = rtorrent.common.find_torrent(torrent.info_hash,
                                                       self.torrents)
            if new_torrent is not None:
                new_torrent.files = torrent.files
                new_torrent.peers = torrent.peers
                new_torrent.trackers = torrent.trackers

        self._torrent_cache = self.torrents

    def _get_load_function(self, file_type, start, verbose):
        """Determine correct "load torrent" RPC method"""
        func_name = None
        if file_type == "url":
            # url strings can be input directly
            if start and verbose:
                func_name = "load.start_verbose"
            elif start:
                func_name = "load.start"
            elif verbose:
                func_name = "load.verbose"
            else:
                func_name = "load.normal"
        elif file_type in ["file", "raw"]:
            if start and verbose:
                func_name = "load.raw_start_verbose"
            elif start:
                func_name = "load.raw_start"
            elif verbose:
                func_name = "load.raw_verbose"
            else:
                func_name = "load.raw"

        return(func_name)

    def load_magnet(self, magneturl, info_hash, start=False, verbose=False, verify_load=True, verify_retries=3):

        p = self._get_conn()

        info_hash = info_hash.upper()

        func_name = self._get_load_function("url", start, verbose)

        # rtorrent > 0.9.6 requires first parameter @target
        target = ""
        # load magnet
        getattr(p, func_name)(target, magneturl)

        if verify_load:
            magnet = False
            i = 0
            while i < verify_retries:
                for m in self.get_torrents():
                    # This block finds the magnet that was just added, starts it, breaks
                    # out of the for loop, and then out of the while loop.
                    # If it can't find the magnet, magnet won't get defined.
                    if m.info_hash == info_hash:
                        magnet = m
                        magnet.start()
                        i += 999
                        break

                # If torrent hasn't been defined, sleep for a second and check again.
                if not magnet:
                    time.sleep(1)
                    i += 1

            # This bit waits for the magnet to be resolved into an actual
            # torrent, and then starts it.
            torrent = False
            i = 0
            while i < verify_retries:
                for t in self.get_torrents():
                    if t.info_hash == info_hash:
                        if str(info_hash) not in str(t.name):
                            torrent = t
                            torrent.start()
                            i += 999
                            break
                if not torrent:
                    time.sleep(1)
                    i += 1

            assert info_hash in [t.info_hash for t in self.torrents],\
                "Adding magnet was unsuccessful."


        return(torrent)

    def load_torrent(self, torrent, start=False, verbose=False, verify_load=True, verify_retries=3):
        """
        Loads torrent into rTorrent (with various enhancements)

        @param torrent: can be a url, a path to a local file, or the raw data
        of a torrent file
        @type torrent: str

        @param start: start torrent when loaded
        @type start: bool

        @param verbose: print error messages to rTorrent log
        @type verbose: bool

        @param verify_load: verify that torrent was added to rTorrent successfully
        @type verify_load: bool

        @return: Depends on verify_load:
                 - if verify_load is True, (and the torrent was
                 loaded successfully), it'll return a L{Torrent} instance
                 - if verify_load is False, it'll return None

        @rtype: L{Torrent} instance or None

        @raise AssertionError: If the torrent wasn't successfully added to rTorrent
                               - Check L{TorrentParser} for the AssertionError's
                               it raises


        @note: Because this function includes url verification (if a url was input)
        as well as verification as to whether the torrent was successfully added,
        this function doesn't execute instantaneously. If that's what you're
        looking for, use load_torrent_simple() instead.
        """
        p = self._get_conn()
        tp = TorrentParser(torrent)
        torrent = xmlrpclib.Binary(tp._raw_torrent)
        info_hash = tp.info_hash

        func_name = self._get_load_function("raw", start, verbose)

        # load torrent
        # rtorrent > 0.9.6 requires first parameter @target
        target = ""
        getattr(p, func_name)(target, torrent)

        if verify_load:
            i = 0
            while i < verify_retries:
                self.get_torrents()
                if info_hash in [t.info_hash for t in self.torrents]:
                    break

                # was still getting AssertionErrors, delay should help
                time.sleep(1)
                i += 1

            assert info_hash in [t.info_hash for t in self.torrents],\
                "Adding torrent was unsuccessful."

        return(find_torrent(info_hash, self.torrents))

    def load_torrent_simple(self, torrent, file_type,
                            start=False, verbose=False):
        """Loads torrent into rTorrent

        @param torrent: can be a url, a path to a local file, or the raw data
        of a torrent file
        @type torrent: str

        @param file_type: valid options: "url", "file", or "raw"
        @type file_type: str

        @param start: start torrent when loaded
        @type start: bool

        @param verbose: print error messages to rTorrent log
        @type verbose: bool

        @return: None

        @raise AssertionError: if incorrect file_type is specified

        @note: This function was written for speed, it includes no enhancements.
        If you input a url, it won't check if it's valid. You also can't get
        verification that the torrent was successfully added to rTorrent.
        Use load_torrent() if you would like these features.
        """
        p = self._get_conn()

        assert file_type in ["raw", "file", "url"], \
            "Invalid file_type, options are: 'url', 'file', 'raw'."
        func_name = self._get_load_function(file_type, start, verbose)

        if file_type == "file":
            # since we have to assume we're connected to a remote rTorrent
            # client, we have to read the file and send it to rT as raw
            assert os.path.isfile(torrent), \
                "Invalid path: \"{0}\"".format(torrent)
            torrent = open(torrent, "rb").read()

        if file_type in ["raw", "file"]:
            finput = xmlrpclib.Binary(torrent)
        elif file_type == "url":
            finput = torrent

        # rtorrent > 0.9.6 requires first parameter @target
        target = ""
        getattr(p, func_name)(target, finput)

    def get_views(self):
        p = self._get_conn()
        return p.view_list()

    def create_group(self, name, persistent=True, view=None):
        p = self._get_conn()

        if persistent is True:
            p.group.insert_persistent_view('', name)
        else:
            assert view is not None, "view parameter required on non-persistent groups"
            p.group.insert('', name, view)

        self.connection._update_rpc_methods()

    def get_group(self, name):
        assert name is not None, "group name required"

        group = Group(self, name)
        group.update()
        return group

    def set_dht_port(self, port):
        """Set DHT port

        @param port: port
        @type port: int

        @raise AssertionError: if invalid port is given
        """
        assert is_valid_port(port), "Valid port range is 0-65535"
        self.dht_port = self._p.set_dht_port(port)

    def enable_check_hash(self):
        """Alias for set_check_hash(True)"""
        self.set_check_hash(True)

    def disable_check_hash(self):
        """Alias for set_check_hash(False)"""
        self.set_check_hash(False)

    def find_torrent(self, info_hash):
        """Frontend for rtorrent.common.find_torrent"""
        return(rtorrent.common.find_torrent(info_hash, self.get_torrents()))

    def poll(self):
        """ poll rTorrent to get latest torrent/peer/tracker/file information

        @note: This essentially refreshes every aspect of the rTorrent
        connection, so it can be very slow if working with a remote
        connection that has a lot of torrents loaded.

        @return: None
        """
        self.update()
        torrents = self.get_torrents()
        for t in torrents:
            t.poll()

    def update(self):
        """Refresh rTorrent client info

        @note: All fields are stored as attributes to self.

        @return: None
        """
        multicall = rtorrent.rpc.Multicall(self)
        retriever_methods = [m for m in methods
                             if m.is_retriever() and m.is_available(self)]
        for method in retriever_methods:
            multicall.add(method)

        multicall.call()


def _build_class_methods(class_obj):
    # multicall add class
    caller = lambda self, multicall, method, *args:\
        multicall.add(method, self.rpc_id, *args)

    caller.__doc__ = """Same as Multicall.add(), but with automatic inclusion
                        of the rpc_id

                        @param multicall: A L{Multicall} instance
                        @type: multicall: Multicall

                        @param method: L{Method} instance or raw rpc method
                        @type: Method or str

                        @param args: optional arguments to pass
                        """
    setattr(class_obj, "multicall_add", caller)


def __compare_rpc_methods(rt_new, rt_old):
    from pprint import pprint
    rt_new_methods = set(rt_new.connection._get_rpc_methods())
    rt_old_methods = set(rt_old.connection._get_rpc_methods())
    print("New Methods:")
    pprint(rt_new_methods - rt_old_methods)
    print("Methods not in new rTorrent:")
    pprint(rt_old_methods - rt_new_methods)


def __check_supported_methods(rt):
    from pprint import pprint
    supported_methods = set([m.rpc_call for m in
                             methods +
                             rtorrent.file.methods +
                             rtorrent.torrent.methods +
                             rtorrent.tracker.methods +
                             rtorrent.peer.methods])
    all_methods = set(rt.connection._get_rpc_methods())

    print("Methods NOT in supported methods")
    pprint(all_methods - supported_methods)
    print("Supported methods NOT in all methods")
    pprint(supported_methods - all_methods)

methods = [
    # RETRIEVERS
    Method(RTorrent, 'get_xmlrpc_size_limit', 'get_xmlrpc_size_limit'),
    Method(RTorrent, 'get_proxy_address', 'get_proxy_address'),
    Method(RTorrent, 'get_split_suffix', 'get_split_suffix'),
    Method(RTorrent, 'get_up_limit', 'get_upload_rate'),
    Method(RTorrent, 'get_max_memory_usage', 'get_max_memory_usage'),
    Method(RTorrent, 'get_max_open_files', 'get_max_open_files'),
    Method(RTorrent, 'get_min_peers_seed', 'get_min_peers_seed'),
    Method(RTorrent, 'get_use_udp_trackers', 'get_use_udp_trackers'),
    Method(RTorrent, 'get_preload_min_size', 'get_preload_min_size'),
    Method(RTorrent, 'get_max_uploads', 'get_max_uploads'),
    Method(RTorrent, 'get_max_peers', 'get_max_peers'),
    Method(RTorrent, 'get_timeout_sync', 'get_timeout_sync'),
    Method(RTorrent, 'get_receive_buffer_size', 'get_receive_buffer_size'),
    Method(RTorrent, 'get_split_file_size', 'get_split_file_size'),
    Method(RTorrent, 'get_dht_throttle', 'get_dht_throttle'),
    Method(RTorrent, 'get_max_peers_seed', 'get_max_peers_seed'),
    Method(RTorrent, 'get_min_peers', 'get_min_peers'),
    Method(RTorrent, 'get_tracker_numwant', 'get_tracker_numwant'),
    Method(RTorrent, 'get_max_open_sockets', 'get_max_open_sockets'),
    Method(RTorrent, 'get_session', 'get_session'),
    Method(RTorrent, 'get_ip', 'get_ip'),
    Method(RTorrent, 'get_scgi_dont_route', 'get_scgi_dont_route'),
    Method(RTorrent, 'get_hash_read_ahead', 'get_hash_read_ahead'),
    Method(RTorrent, 'get_http_cacert', 'get_http_cacert'),
    Method(RTorrent, 'get_dht_port', 'get_dht_port'),
    Method(RTorrent, 'get_handshake_log', 'get_handshake_log'),
    Method(RTorrent, 'get_preload_type', 'get_preload_type'),
    Method(RTorrent, 'get_max_open_http', 'get_max_open_http'),
    Method(RTorrent, 'get_http_capath', 'get_http_capath'),
    Method(RTorrent, 'get_max_downloads_global', 'get_max_downloads_global'),
    Method(RTorrent, 'get_name', 'get_name'),
    Method(RTorrent, 'get_session_on_completion', 'get_session_on_completion'),
    Method(RTorrent, 'get_down_limit', 'get_download_rate'),
    Method(RTorrent, 'get_down_total', 'get_down_total'),
    Method(RTorrent, 'get_up_rate', 'get_up_rate'),
    Method(RTorrent, 'get_hash_max_tries', 'get_hash_max_tries'),
    Method(RTorrent, 'get_peer_exchange', 'get_peer_exchange'),
    Method(RTorrent, 'get_down_rate', 'get_down_rate'),
    Method(RTorrent, 'get_connection_seed', 'get_connection_seed'),
    Method(RTorrent, 'get_http_proxy', 'get_http_proxy'),
    Method(RTorrent, 'get_stats_preloaded', 'get_stats_preloaded'),
    Method(RTorrent, 'get_timeout_safe_sync', 'get_timeout_safe_sync'),
    Method(RTorrent, 'get_hash_interval', 'get_hash_interval'),
    Method(RTorrent, 'get_port_random', 'get_port_random'),
    Method(RTorrent, 'get_directory', 'get_directory'),
    Method(RTorrent, 'get_port_open', 'get_port_open'),
    Method(RTorrent, 'get_max_file_size', 'get_max_file_size'),
    Method(RTorrent, 'get_stats_not_preloaded', 'get_stats_not_preloaded'),
    Method(RTorrent, 'get_memory_usage', 'get_memory_usage'),
    Method(RTorrent, 'get_connection_leech', 'get_connection_leech'),
    Method(RTorrent, 'get_check_hash', 'get_check_hash',
           boolean=True,
           ),
    Method(RTorrent, 'get_session_lock', 'get_session_lock'),
    Method(RTorrent, 'get_preload_required_rate', 'get_preload_required_rate'),
    Method(RTorrent, 'get_max_uploads_global', 'get_max_uploads_global'),
    Method(RTorrent, 'get_send_buffer_size', 'get_send_buffer_size'),
    Method(RTorrent, 'get_port_range', 'get_port_range'),
    Method(RTorrent, 'get_max_downloads_div', 'get_max_downloads_div'),
    Method(RTorrent, 'get_max_uploads_div', 'get_max_uploads_div'),
    Method(RTorrent, 'get_safe_sync', 'get_safe_sync'),
    Method(RTorrent, 'get_bind', 'get_bind'),
    Method(RTorrent, 'get_up_total', 'get_up_total'),
    Method(RTorrent, 'get_client_version', 'system.client_version'),
    Method(RTorrent, 'get_library_version', 'system.library_version'),
    Method(RTorrent, 'get_api_version', 'system.api_version',
           min_version=(0, 9, 1)
           ),
    Method(RTorrent, "get_system_time", "system.time",
           docstring="""Get the current time of the system rTorrent is running on

           @return: time (posix)
           @rtype: int""",
           ),

    # MODIFIERS
    Method(RTorrent, 'set_http_proxy', 'set_http_proxy'),
    Method(RTorrent, 'set_max_memory_usage', 'set_max_memory_usage'),
    Method(RTorrent, 'set_max_file_size', 'set_max_file_size'),
    Method(RTorrent, 'set_bind', 'set_bind',
           docstring="""Set address bind

           @param arg: ip address
           @type arg: str
           """,
           ),
    Method(RTorrent, 'set_up_limit', 'set_upload_rate',
           docstring="""Set global upload limit (in bytes)

           @param arg: speed limit
           @type arg: int
           """,
           ),
    Method(RTorrent, 'set_port_random', 'set_port_random'),
    Method(RTorrent, 'set_connection_leech', 'set_connection_leech'),
    Method(RTorrent, 'set_tracker_numwant', 'set_tracker_numwant'),
    Method(RTorrent, 'set_max_peers', 'set_max_peers'),
    Method(RTorrent, 'set_min_peers', 'set_min_peers'),
    Method(RTorrent, 'set_max_uploads_div', 'set_max_uploads_div'),
    Method(RTorrent, 'set_max_open_files', 'set_max_open_files'),
    Method(RTorrent, 'set_max_downloads_global', 'set_max_downloads_global'),
    Method(RTorrent, 'set_session_lock', 'set_session_lock'),
    Method(RTorrent, 'set_session', 'set_session'),
    Method(RTorrent, 'set_split_suffix', 'set_split_suffix'),
    Method(RTorrent, 'set_hash_interval', 'set_hash_interval'),
    Method(RTorrent, 'set_handshake_log', 'set_handshake_log'),
    Method(RTorrent, 'set_port_range', 'set_port_range'),
    Method(RTorrent, 'set_min_peers_seed', 'set_min_peers_seed'),
    Method(RTorrent, 'set_scgi_dont_route', 'set_scgi_dont_route'),
    Method(RTorrent, 'set_preload_min_size', 'set_preload_min_size'),
    Method(RTorrent, 'set_log.tracker', 'set_log.tracker'),
    Method(RTorrent, 'set_max_uploads_global', 'set_max_uploads_global'),
    Method(RTorrent, 'set_down_limit', 'set_download_rate',
           docstring="""Set global download limit (in bytes)

           @param arg: speed limit
           @type arg: int
           """,
           ),
    Method(RTorrent, 'set_preload_required_rate', 'set_preload_required_rate'),
    Method(RTorrent, 'set_hash_read_ahead', 'set_hash_read_ahead'),
    Method(RTorrent, 'set_max_peers_seed', 'set_max_peers_seed'),
    Method(RTorrent, 'set_max_uploads', 'set_max_uploads'),
    Method(RTorrent, 'set_session_on_completion', 'set_session_on_completion'),
    Method(RTorrent, 'set_max_open_http', 'set_max_open_http'),
    Method(RTorrent, 'set_directory', 'set_directory'),
    Method(RTorrent, 'set_http_cacert', 'set_http_cacert'),
    Method(RTorrent, 'set_dht_throttle', 'set_dht_throttle'),
    Method(RTorrent, 'set_hash_max_tries', 'set_hash_max_tries'),
    Method(RTorrent, 'set_proxy_address', 'set_proxy_address'),
    Method(RTorrent, 'set_split_file_size', 'set_split_file_size'),
    Method(RTorrent, 'set_receive_buffer_size', 'set_receive_buffer_size'),
    Method(RTorrent, 'set_use_udp_trackers', 'set_use_udp_trackers'),
    Method(RTorrent, 'set_connection_seed', 'set_connection_seed'),
    Method(RTorrent, 'set_xmlrpc_size_limit', 'set_xmlrpc_size_limit'),
    Method(RTorrent, 'set_xmlrpc_dialect', 'set_xmlrpc_dialect'),
    Method(RTorrent, 'set_safe_sync', 'set_safe_sync'),
    Method(RTorrent, 'set_http_capath', 'set_http_capath'),
    Method(RTorrent, 'set_send_buffer_size', 'set_send_buffer_size'),
    Method(RTorrent, 'set_max_downloads_div', 'set_max_downloads_div'),
    Method(RTorrent, 'set_name', 'set_name'),
    Method(RTorrent, 'set_port_open', 'set_port_open'),
    Method(RTorrent, 'set_timeout_sync', 'set_timeout_sync'),
    Method(RTorrent, 'set_peer_exchange', 'set_peer_exchange'),
    Method(RTorrent, 'set_ip', 'set_ip',
           docstring="""Set IP

           @param arg: ip address
           @type arg: str
           """,
           ),
    Method(RTorrent, 'set_timeout_safe_sync', 'set_timeout_safe_sync'),
    Method(RTorrent, 'set_preload_type', 'set_preload_type'),
    Method(RTorrent, 'set_check_hash', 'set_check_hash',
           docstring="""Enable/Disable hash checking on finished torrents

            @param arg: True to enable, False to disable
            @type arg: bool
            """,
           boolean=True,
           ),
]

_all_methods_list = [methods,
                     rtorrent.file.methods,
                     rtorrent.torrent.methods,
                     rtorrent.tracker.methods,
                     rtorrent.peer.methods,
                     ]

class_methods_pair = {
    RTorrent: methods,
    rtorrent.file.File: rtorrent.file.methods,
    rtorrent.torrent.Torrent: rtorrent.torrent.methods,
    rtorrent.tracker.Tracker: rtorrent.tracker.methods,
    rtorrent.peer.Peer: rtorrent.peer.methods,
}
for c in class_methods_pair.keys():
    rtorrent.rpc._build_rpc_methods(c, class_methods_pair[c])
    _build_class_methods(c)
