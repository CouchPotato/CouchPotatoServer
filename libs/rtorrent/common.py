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


from rtorrent.compat import is_py3


def bool_to_int(value):
    """Translates python booleans to RPC-safe integers"""
    if value is True:
        return("1")
    elif value is False:
        return("0")
    else:
        return(value)


def cmd_exists(cmds_list, cmd):
    """Check if given command is in list of available commands

    @param cmds_list: see L{RTorrent._rpc_methods}
    @type cmds_list: list

    @param cmd: name of command to be checked
    @type cmd: str

    @return: bool
    """

    return(cmd in cmds_list)


def find_torrent(info_hash, torrent_list):
    """Find torrent file in given list of Torrent classes

    @param info_hash: info hash of torrent
    @type info_hash: str

    @param torrent_list: list of L{Torrent} instances (see L{RTorrent.get_torrents})
    @type torrent_list: list

    @return: L{Torrent} instance, or -1 if not found
    """
    for t in torrent_list:
        if t.info_hash == info_hash:
            return t

    return None


def is_valid_port(port):
    """Check if given port is valid"""
    return(0 <= int(port) <= 65535)


def convert_version_tuple_to_str(t):
    return(".".join([str(n) for n in t]))


def safe_repr(fmt, *args, **kwargs):
    """ Formatter that handles unicode arguments """

    if not is_py3():
        # unicode fmt can take str args, str fmt cannot take unicode args
        fmt = fmt.decode("utf-8")
        out = fmt.format(*args, **kwargs)
        return out.encode("utf-8")
    else:
        return fmt.format(*args, **kwargs)
