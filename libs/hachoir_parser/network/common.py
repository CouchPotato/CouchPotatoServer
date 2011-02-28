from hachoir_core.field import FieldSet, Field, Bits
from hachoir_core.bits import str2hex
from hachoir_parser.network.ouid import REGISTERED_OUID
from hachoir_core.endian import BIG_ENDIAN
from socket import gethostbyaddr, herror as socket_host_error

def ip2name(addr):
    if not ip2name.resolve:
        return addr
    try:
        if addr in ip2name.cache:
            return ip2name.cache[addr]
        # FIXME: Workaround Python bug
        # Need double try/except to catch the bug
        try:
            name = gethostbyaddr(addr)[0]
        except KeyboardInterrupt:
            raise
    except (socket_host_error, ValueError):
        name = addr
    except (socket_host_error, KeyboardInterrupt, ValueError):
        ip2name.resolve = False
        name = addr
    ip2name.cache[addr] = name
    return name
ip2name.cache = {}
ip2name.resolve = True

class IPv4_Address(Field):
    def __init__(self, parent, name, description=None):
        Field.__init__(self, parent, name, 32, description)

    def createValue(self):
        value = self._parent.stream.readBytes(self.absolute_address, 4)
        return ".".join(( "%u" % ord(byte) for byte in value ))

    def createDisplay(self):
        return ip2name(self.value)

class IPv6_Address(Field):
    def __init__(self, parent, name, description=None):
        Field.__init__(self, parent, name, 128, description)

    def createValue(self):
        value = self._parent.stream.readBits(self.absolute_address, 128, self.parent.endian)
        parts = []
        for index in xrange(8):
            part = "%04x" % (value & 0xffff)
            value >>= 16
            parts.append(part)
        return ':'.join(reversed(parts))

    def createDisplay(self):
        return self.value

class OrganizationallyUniqueIdentifier(Bits):
    """
    IEEE 24-bit Organizationally unique identifier
    """
    static_size = 24

    def __init__(self, parent, name, description=None):
        Bits.__init__(self, parent, name, 24, description=None)

    def createDisplay(self, human=True):
        if human:
            key = self.value
            if key in REGISTERED_OUID:
                return REGISTERED_OUID[key]
            else:
                return self.raw_display
        else:
            return self.raw_display

    def createRawDisplay(self):
        value = self.value
        a = value >> 16
        b = (value >> 8) & 0xFF
        c = value & 0xFF
        return "%02X-%02X-%02X" % (a, b, c)

class NIC24(Bits):
    static_size = 24

    def __init__(self, parent, name, description=None):
        Bits.__init__(self, parent, name, 24, description=None)

    def createDisplay(self):
        value = self.value
        a = value >> 16
        b = (value >> 8) & 0xFF
        c = value & 0xFF
        return "%02x:%02x:%02x" % (a, b, c)

    def createRawDisplay(self):
        return "0x%06X" % self.value

class MAC48_Address(FieldSet):
    """
    IEEE 802 48-bit MAC address
    """
    static_size = 48
    endian = BIG_ENDIAN

    def createFields(self):
        yield OrganizationallyUniqueIdentifier(self, "organization")
        yield NIC24(self, "nic")

    def hasValue(self):
        return True

    def createValue(self):
        bytes = self.stream.readBytes(self.absolute_address, 6)
        return str2hex(bytes, format="%02x:")[:-1]

    def createDisplay(self):
        return "%s [%s]" % (self["organization"].display, self["nic"].display)

