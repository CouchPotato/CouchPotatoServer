from cStringIO import StringIO
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.bits import long2raw
from hachoir_core.stream import StreamError
from errno import EBADF

MAX_READ_NBYTES = 2 ** 16

class OutputStreamError(StreamError):
    pass

class OutputStream(object):
    def __init__(self, output, filename=None):
        self._output = output
        self._filename = filename
        self._bit_pos = 0
        self._byte = 0

    def _getFilename(self):
        return self._filename
    filename = property(_getFilename)

    def writeBit(self, state, endian):
        if self._bit_pos == 7:
            self._bit_pos = 0
            if state:
                if endian is BIG_ENDIAN:
                    self._byte |= 1
                else:
                    self._byte |= 128
            self._output.write(chr(self._byte))
            self._byte = 0
        else:
            if state:
                if endian is BIG_ENDIAN:
                    self._byte |= (1 << self._bit_pos)
                else:
                    self._byte |= (1 << (7-self._bit_pos))
            self._bit_pos += 1

    def writeBits(self, count, value, endian):
        assert 0 <= value < 2**count

        # Feed bits to align to byte address
        if self._bit_pos != 0:
            n = 8 - self._bit_pos
            if n <= count:
                count -= n
                if endian is BIG_ENDIAN:
                    self._byte |= (value >> count)
                    value &= ((1 << count) - 1)
                else:
                    self._byte |= (value & ((1 << n)-1)) << self._bit_pos
                    value >>= n
                self._output.write(chr(self._byte))
                self._bit_pos = 0
                self._byte = 0
            else:
                if endian is BIG_ENDIAN:
                    self._byte |= (value << (8-self._bit_pos-count))
                else:
                    self._byte |= (value << self._bit_pos)
                self._bit_pos += count
                return

        # Write byte per byte
        while 8 <= count:
            count -= 8
            if endian is BIG_ENDIAN:
                byte = (value >> count)
                value &= ((1 << count) - 1)
            else:
                byte = (value & 0xFF)
                value >>= 8
            self._output.write(chr(byte))

        # Keep last bits
        assert 0 <= count < 8
        self._bit_pos = count
        if 0 < count:
            assert 0 <= value < 2**count
            if endian is BIG_ENDIAN:
                self._byte = value << (8-count)
            else:
                self._byte = value
        else:
            assert value == 0
            self._byte = 0

    def writeInteger(self, value, signed, size_byte, endian):
        if signed:
            value += 1 << (size_byte*8 - 1)
        raw = long2raw(value, endian, size_byte)
        self.writeBytes(raw)

    def copyBitsFrom(self, input, address, nb_bits, endian):
        if (nb_bits % 8) == 0:
            self.copyBytesFrom(input, address, nb_bits/8)
        else:
            # Arbitrary limit (because we should use a buffer, like copyBytesFrom(),
            # but with endianess problem
            assert nb_bits <= 128
            data = input.readBits(address, nb_bits, endian)
            self.writeBits(nb_bits, data, endian)

    def copyBytesFrom(self, input, address, nb_bytes):
        if (address % 8):
            raise OutputStreamError("Unable to copy bytes with address with bit granularity")
        buffer_size = 1 << 12   # 8192 (8 KB)
        while 0 < nb_bytes:
            # Compute buffer size
            if nb_bytes < buffer_size:
                buffer_size = nb_bytes

            # Read
            data = input.readBytes(address, buffer_size)

            # Write
            self.writeBytes(data)

            # Move address
            address += buffer_size*8
            nb_bytes -= buffer_size

    def writeBytes(self, bytes):
        if self._bit_pos != 0:
            raise NotImplementedError()
        self._output.write(bytes)

    def readBytes(self, address, nbytes):
        """
        Read bytes from the stream at specified address (in bits).
        Address have to be a multiple of 8.
        nbytes have to in 1..MAX_READ_NBYTES (64 KB).

        This method is only supported for StringOuputStream (not on
        FileOutputStream).

        Return read bytes as byte string.
        """
        assert (address % 8) == 0
        assert (1 <= nbytes <= MAX_READ_NBYTES)
        self._output.flush()
        oldpos = self._output.tell()
        try:
            self._output.seek(0)
            try:
                return self._output.read(nbytes)
            except IOError, err:
                if err[0] == EBADF:
                    raise OutputStreamError("Stream doesn't support read() operation")
        finally:
            self._output.seek(oldpos)

def StringOutputStream():
    """
    Create an output stream into a string.
    """
    data = StringIO()
    return OutputStream(data)

def FileOutputStream(filename, real_filename=None):
    """
    Create an output stream into file with given name.

    Filename have to be unicode, whereas (optional) real_filename can be str.
    """
    assert isinstance(filename, unicode)
    if not real_filename:
        real_filename = filename
    output = open(real_filename, 'wb')
    return OutputStream(output, filename=filename)

