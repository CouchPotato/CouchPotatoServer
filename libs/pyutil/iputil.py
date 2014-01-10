# from the Python Standard Library
import os, re, socket, sys, subprocess

# from Twisted
from twisted.internet import defer, threads, reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.python.procutils import which
from twisted.python import log

try:
    import resource
    def increase_rlimits():
        # We'd like to raise our soft resource.RLIMIT_NOFILE, since certain
        # systems (OS-X, probably solaris) start with a relatively low limit
        # (256), and some unit tests want to open up more sockets than this.
        # Most linux systems start with both hard and soft limits at 1024,
        # which is plenty.

        # unfortunately the values to pass to setrlimit() vary widely from
        # one system to another. OS-X reports (256, HUGE), but the real hard
        # limit is 10240, and accepts (-1,-1) to mean raise it to the
        # maximum. Cygwin reports (256, -1), then ignores a request of
        # (-1,-1): instead you have to guess at the hard limit (it appears to
        # be 3200), so using (3200,-1) seems to work. Linux reports a
        # sensible (1024,1024), then rejects (-1,-1) as trying to raise the
        # maximum limit, so you could set it to (1024,1024) but you might as
        # well leave it alone.

        try:
            current = resource.getrlimit(resource.RLIMIT_NOFILE)
        except AttributeError:
            # we're probably missing RLIMIT_NOFILE
            return

        if current[0] >= 1024:
            # good enough, leave it alone
            return

        try:
            if current[1] > 0 and current[1] < 1000000:
                # solaris reports (256, 65536)
                resource.setrlimit(resource.RLIMIT_NOFILE,
                                   (current[1], current[1]))
            else:
                # this one works on OS-X (bsd), and gives us 10240, but
                # it doesn't work on linux (on which both the hard and
                # soft limits are set to 1024 by default).
                resource.setrlimit(resource.RLIMIT_NOFILE, (-1,-1))
                new = resource.getrlimit(resource.RLIMIT_NOFILE)
                if new[0] == current[0]:
                    # probably cygwin, which ignores -1. Use a real value.
                    resource.setrlimit(resource.RLIMIT_NOFILE, (3200,-1))

        except ValueError:
            log.msg("unable to set RLIMIT_NOFILE: current value %s"
                     % (resource.getrlimit(resource.RLIMIT_NOFILE),))
        except:
            # who knows what. It isn't very important, so log it and continue
            log.err()
except ImportError:
    def _increase_rlimits():
        # TODO: implement this for Windows.  Although I suspect the
        # solution might be "be running under the iocp reactor and
        # make this function be a no-op".
        pass
    # pyflakes complains about two 'def FOO' statements in the same time,
    # since one might be shadowing the other. This hack appeases pyflakes.
    increase_rlimits = _increase_rlimits


def get_local_addresses_async(target="198.41.0.4"): # A.ROOT-SERVERS.NET
    """
    Return a Deferred that fires with a list of IPv4 addresses (as dotted-quad
    strings) that are currently configured on this host, sorted in descending
    order of how likely we think they are to work.

    @param target: we want to learn an IP address they could try using to
        connect to us; The default value is fine, but it might help if you
        pass the address of a host that you are actually trying to be
        reachable to.
    """
    addresses = []
    local_ip = get_local_ip_for(target)
    if local_ip:
        addresses.append(local_ip)

    if sys.platform == "cygwin":
        d = _cygwin_hack_find_addresses(target)
    else:
        d = _find_addresses_via_config()

    def _collect(res):
        for addr in res:
            if addr != "0.0.0.0" and not addr in addresses:
                addresses.append(addr)
        return addresses
    d.addCallback(_collect)

    return d

def get_local_ip_for(target):
    """Find out what our IP address is for use by a given target.

    @return: the IP address as a dotted-quad string which could be used by
              to connect to us. It might work for them, it might not. If
              there is no suitable address (perhaps we don't currently have an
              externally-visible interface), this will return None.
    """

    try:
        target_ipaddr = socket.gethostbyname(target)
    except socket.gaierror:
        # DNS isn't running, or somehow we encountered an error

        # note: if an interface is configured and up, but nothing is
        # connected to it, gethostbyname("A.ROOT-SERVERS.NET") will take 20
        # seconds to raise socket.gaierror . This is synchronous and occurs
        # for each node being started, so users of
        # test.common.SystemTestMixin (like test_system) will see something
        # like 120s of delay, which may be enough to hit the default trial
        # timeouts. For that reason, get_local_addresses_async() was changed
        # to default to the numerical ip address for A.ROOT-SERVERS.NET, to
        # avoid this DNS lookup. This also makes node startup fractionally
        # faster.
        return None
    udpprot = DatagramProtocol()
    port = reactor.listenUDP(0, udpprot)
    try:
        udpprot.transport.connect(target_ipaddr, 7)
        localip = udpprot.transport.getHost().host
    except socket.error:
        # no route to that host
        localip = None
    port.stopListening() # note, this returns a Deferred
    return localip

# k: result of sys.platform, v: which kind of IP configuration reader we use
_platform_map = {
    "linux-i386": "linux", # redhat
    "linux-ppc": "linux",  # redhat
    "linux2": "linux",     # debian
    "linux3": "linux",     # debian
    "win32": "win32",
    "irix6-n32": "irix",
    "irix6-n64": "irix",
    "irix6": "irix",
    "openbsd2": "bsd",
    "openbsd3": "bsd",
    "openbsd4": "bsd",
    "openbsd5": "bsd",
    "darwin": "bsd",       # Mac OS X
    "freebsd4": "bsd",
    "freebsd5": "bsd",
    "freebsd6": "bsd",
    "freebsd7": "bsd",
    "freebsd8": "bsd",
    "freebsd9": "bsd",
    "netbsd1": "bsd",
    "netbsd2": "bsd",
    "netbsd3": "bsd",
    "netbsd4": "bsd",
    "netbsd5": "bsd",
    "netbsd6": "bsd",
    "dragonfly2": "bsd",
    "sunos5": "sunos",
    "cygwin": "cygwin",
    }

class UnsupportedPlatformError(Exception):
    pass

# Wow, I'm really amazed at home much mileage we've gotten out of calling
# the external route.exe program on windows...  It appears to work on all
# versions so far.  Still, the real system calls would much be preferred...
# ... thus wrote Greg Smith in time immemorial...
_win32_path = 'route.exe'
_win32_args = ('print',)
_win32_re = re.compile('^\s*\d+\.\d+\.\d+\.\d+\s.+\s(?P<address>\d+\.\d+\.\d+\.\d+)\s+(?P<metric>\d+)\s*$', flags=re.M|re.I|re.S)

# These work in Redhat 6.x and Debian 2.2 potato
_linux_path = '/sbin/ifconfig'
_linux_re = re.compile('^\s*inet [a-zA-Z]*:?(?P<address>\d+\.\d+\.\d+\.\d+)\s.+$', flags=re.M|re.I|re.S)

# NetBSD 1.4 (submitted by Rhialto), Darwin, Mac OS X
_netbsd_path = '/sbin/ifconfig'
_netbsd_args = ('-a',)
_netbsd_re = re.compile('^\s+inet [a-zA-Z]*:?(?P<address>\d+\.\d+\.\d+\.\d+)\s.+$', flags=re.M|re.I|re.S)

# Irix 6.5
_irix_path = '/usr/etc/ifconfig'

# Solaris 2.x
_sunos_path = '/usr/sbin/ifconfig'


# k: platform string as provided in the value of _platform_map
# v: tuple of (path_to_tool, args, regex,)
_tool_map = {
    "linux": (_linux_path, (), _linux_re,),
    "win32": (_win32_path, _win32_args, _win32_re,),
    "cygwin": (_win32_path, _win32_args, _win32_re,),
    "bsd": (_netbsd_path, _netbsd_args, _netbsd_re,),
    "irix": (_irix_path, _netbsd_args, _netbsd_re,),
    "sunos": (_sunos_path, _netbsd_args, _netbsd_re,),
    }

def _find_addresses_via_config():
    return threads.deferToThread(_synchronously_find_addresses_via_config)

def _synchronously_find_addresses_via_config():
    # originally by Greg Smith, hacked by Zooko to conform to Brian's API

    platform = _platform_map.get(sys.platform)
    if not platform:
        raise UnsupportedPlatformError(sys.platform)

    (pathtotool, args, regex,) = _tool_map[platform]

    # If pathtotool is a fully qualified path then we just try that.
    # If it is merely an executable name then we use Twisted's
    # "which()" utility and try each executable in turn until one
    # gives us something that resembles a dotted-quad IPv4 address.

    if os.path.isabs(pathtotool):
        return _query(pathtotool, args, regex)
    else:
        exes_to_try = which(pathtotool)
        for exe in exes_to_try:
            try:
                addresses = _query(exe, args, regex)
            except Exception:
                addresses = []
            if addresses:
                return addresses
        return []

def _query(path, args, regex):
    env = {'LANG': 'en_US.UTF-8'}
    p = subprocess.Popen([path] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    (output, err) = p.communicate()

    addresses = []
    outputsplit = output.split('\n')
    for outline in outputsplit:
        m = regex.match(outline)
        if m:
            addr = m.groupdict()['address']
            if addr not in addresses:
                addresses.append(addr)

    return addresses

def _cygwin_hack_find_addresses(target):
    addresses = []
    for h in [target, "localhost", "127.0.0.1",]:
        try:
            addr = get_local_ip_for(h)
            if addr not in addresses:
                addresses.append(addr)
        except socket.gaierror:
            pass

    return defer.succeed(addresses)
