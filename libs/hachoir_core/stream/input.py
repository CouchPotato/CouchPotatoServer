from hachoir_core.endian import BIG_ENDIAN, LITTLE_ENDIAN
from hachoir_core.error import info
from hachoir_core.log import Logger
from hachoir_core.bits import str2long
from hachoir_core.i18n import getTerminalCharset
from hachoir_core.tools import lowerBound
from hachoir_core.i18n import _
from errno import ESPIPE
from weakref import ref as weakref_ref
from hachoir_core.stream import StreamError

class InputStreamError(StreamError):
    pass

class ReadStreamError(InputStreamError):
    def __init__(self, size, address, got=None):
        self.size = size
        self.address = address
        self.got = got
        if self.got is not None:
            msg = _("Can't read %u bits at address %u (got %u bits)") % (self.size, self.address, self.got)
        else:
            msg = _("Can't read %u bits at address %u") % (self.size, self.address)
        InputStreamError.__init__(self, msg)

class NullStreamError(InputStreamError):
    def __init__(self, source):
        self.source = source
        msg = _("Input size is nul (source='%s')!") % self.source
        InputStreamError.__init__(self, msg)

class FileFromInputStream:
    _offset = 0
    _from_end = False

    def __init__(self, stream):
        self.stream = stream
        self._setSize(stream.askSize(self))

    def _setSize(self, size):
        if size is None:
            self._size = size
        elif size % 8:
            raise InputStreamError("Invalid size")
        else:
            self._size = size // 8

    def tell(self):
        if self._from_end:
            while self._size is None:
                self.stream._feed(max(self.stream._current_size << 1, 1 << 16))
            self._from_end = False
            self._offset += self._size
        return self._offset

    def seek(self, pos, whence=0):
        if whence == 0:
            self._from_end = False
            self._offset = pos
        elif whence == 1:
            self._offset += pos
        elif whence == 2:
            self._from_end = True
            self._offset = pos
        else:
            raise ValueError("seek() second argument must be 0, 1 or 2")

    def read(self, size=None):
        def read(address, size):
            shift, data, missing = self.stream.read(8 * address, 8 * size)
            if shift:
                raise InputStreamError("TODO: handle non-byte-aligned data")
            return data
        if self._size or size is not None and not self._from_end:
            # We don't want self.tell() to read anything
            # and the size must be known if we read until the end.
            pos = self.tell()
            if size is None or None < self._size < pos + size:
                size = self._size - pos
            if size <= 0:
                return ''
            data = read(pos, size)
            self._offset += len(data)
            return data
        elif self._from_end:
            # TODO: not tested
            max_size = - self._offset
            if size is None or max_size < size:
                size = max_size
            if size <= 0:
                return ''
            data = '', ''
            self._offset = max(0, self.stream._current_size // 8 + self._offset)
            self._from_end = False
            bs = max(max_size, 1 << 16)
            while True:
                d = read(self._offset, bs)
                data = data[1], d
                self._offset += len(d)
                if self._size:
                    bs = self._size - self._offset
                    if not bs:
                        data = data[0] + data[1]
                        d = len(data) - max_size
                        return data[d:d+size]
        else:
            # TODO: not tested
            data = [ ]
            size = 1 << 16
            while True:
                d = read(self._offset, size)
                data.append(d)
                self._offset += len(d)
                if self._size:
                    size = self._size - self._offset
                    if not size:
                        return ''.join(data)


class InputStream(Logger):
    _set_size = None
    _current_size = 0

    def __init__(self, source=None, size=None, packets=None, **args):
        self.source = source
        self._size = size   # in bits
        if size == 0:
            raise NullStreamError(source)
        self.tags = tuple(args.get("tags", tuple()))
        self.packets = packets

    def askSize(self, client):
        if self._size != self._current_size:
            if self._set_size is None:
                self._set_size = []
            self._set_size.append(weakref_ref(client))
        return self._size

    def _setSize(self, size=None):
        assert self._size is None or self._current_size <= self._size
        if self._size != self._current_size:
            self._size = self._current_size
            if not self._size:
                raise NullStreamError(self.source)
            if self._set_size:
                for client in self._set_size:
                    client = client()
                    if client:
                        client._setSize(self._size)
                del self._set_size

    size = property(lambda self: self._size, doc="Size of the stream in bits")
    checked = property(lambda self: self._size == self._current_size)

    def sizeGe(self, size, const=False):
        return self._current_size >= size or \
            not (None < self._size < size or const or self._feed(size))

    def _feed(self, size):
        return self.read(size-1,1)[2]

    def read(self, address, size):
        """
        Read 'size' bits at position 'address' (in bits)
        from the beginning of the stream.
        """
        raise NotImplementedError

    def readBits(self, address, nbits, endian):
        assert endian in (BIG_ENDIAN, LITTLE_ENDIAN)

        shift, data, missing = self.read(address, nbits)
        if missing:
            raise ReadStreamError(nbits, address)
        value = str2long(data, endian)
        if endian is BIG_ENDIAN:
            value >>= len(data) * 8 - shift - nbits
        else:
            value >>= shift
        return value & (1 << nbits) - 1

    def readInteger(self, address, signed, nbits, endian):
        """ Read an integer number """
        value = self.readBits(address, nbits, endian)

        # Signe number. Example with nbits=8:
        # if 128 <= value: value -= 256
        if signed and (1 << (nbits-1)) <= value:
            value -= (1 << nbits)
        return value

    def readBytes(self, address, nb_bytes):
        shift, data, missing = self.read(address, 8 * nb_bytes)
        if shift:
            raise InputStreamError("TODO: handle non-byte-aligned data")
        if missing:
            raise ReadStreamError(8 * nb_bytes, address)
        return data

    def searchBytesLength(self, needle, include_needle,
    start_address=0, end_address=None):
        """
        If include_needle is True, add its length to the result.
        Returns None is needle can't be found.
        """

        pos = self.searchBytes(needle, start_address, end_address)
        if pos is None:
            return None
        length = (pos - start_address) // 8
        if include_needle:
            length += len(needle)
        return length

    def searchBytes(self, needle, start_address=0, end_address=None):
        """
        Search some bytes in [start_address;end_address[. Addresses must
        be aligned to byte. Returns the address of the bytes if found,
        None else.
        """
        if start_address % 8:
            raise InputStreamError("Unable to search bytes with address with bit granularity")
        length = len(needle)
        size = max(3 * length, 4096)
        buffer = ''

        if self._size and (end_address is None or self._size < end_address):
            end_address = self._size

        while True:
            if end_address is not None:
                todo = (end_address - start_address) >> 3
                if todo < size:
                    if todo <= 0:
                        return None
                    size = todo
            data = self.readBytes(start_address, size)
            if end_address is None and self._size:
                end_address = self._size
                size = (end_address - start_address) >> 3
                assert size > 0
                data = data[:size]
            start_address += 8 * size
            buffer = buffer[len(buffer) - length + 1:] + data
            found = buffer.find(needle)
            if found >= 0:
                return start_address + (found - len(buffer)) * 8

    def file(self):
        return FileFromInputStream(self)


class InputPipe(object):
    """
    InputPipe makes input streams seekable by caching a certain
    amount of data. The memory usage may be unlimited in worst cases.
    A function (set_size) is called when the size of the stream is known.

    InputPipe sees the input stream as an array of blocks of
    size = (2 ^ self.buffer_size) and self.buffers maps to this array.
    It also maintains a circular ordered list of non-discarded blocks,
    sorted by access time.

    Each element of self.buffers is an array of 3 elements:
     * self.buffers[i][0] is the data.
       len(self.buffers[i][0]) == 1 << self.buffer_size
       (except at the end: the length may be smaller)
     * self.buffers[i][1] is the index of a more recently used block
     * self.buffers[i][2] is the opposite of self.buffers[1],
       in order to have a double-linked list.
    For any discarded block, self.buffers[i] = None

    self.last is the index of the most recently accessed block.
    self.first is the first (= smallest index) non-discarded block.

    How InputPipe discards blocks:
     * Just before returning from the read method.
     * Only if there are more than self.buffer_nb_min blocks in memory.
     * While self.buffers[self.first] is that least recently used block.

    Property: There is no hole in self.buffers, except at the beginning.
    """
    buffer_nb_min = 256
    buffer_size = 16
    last = None
    size = None

    def __init__(self, input, set_size=None):
        self._input = input
        self.first = self.address = 0
        self.buffers = []
        self.set_size = set_size

    current_size = property(lambda self: len(self.buffers) << self.buffer_size)

    def _append(self, data):
        if self.last is None:
            self.last = next = prev = 0
        else:
            prev = self.last
            last = self.buffers[prev]
            next = last[1]
            self.last = self.buffers[next][2] = last[1] = len(self.buffers)
        self.buffers.append([ data, next, prev ])

    def _get(self, index):
        if index >= len(self.buffers):
            return ''
        buf = self.buffers[index]
        if buf is None:
            raise InputStreamError(_("Error: Buffers too small. Can't seek backward."))
        if self.last != index:
            next = buf[1]
            prev = buf[2]
            self.buffers[next][2] = prev
            self.buffers[prev][1] = next
            first = self.buffers[self.last][1]
            buf[1] = first
            buf[2] = self.last
            self.buffers[first][2] = index
            self.buffers[self.last][1] = index
            self.last = index
        return buf[0]

    def _flush(self):
        lim = len(self.buffers) - self.buffer_nb_min
        while self.first < lim:
            buf = self.buffers[self.first]
            if buf[2] != self.last:
                break
            info("Discarding buffer %u." % self.first)
            self.buffers[self.last][1] = buf[1]
            self.buffers[buf[1]][2] = self.last
            self.buffers[self.first] = None
            self.first += 1

    def seek(self, address):
        assert 0 <= address
        self.address = address

    def read(self, size):
        end = self.address + size
        for i in xrange(len(self.buffers), (end >> self.buffer_size) + 1):
            data = self._input.read(1 << self.buffer_size)
            if len(data) < 1 << self.buffer_size:
                self.size = (len(self.buffers) << self.buffer_size) + len(data)
                if self.set_size:
                    self.set_size(self.size)
                if data:
                    self._append(data)
                break
            self._append(data)
        block, offset = divmod(self.address, 1 << self.buffer_size)
        data = ''.join(self._get(index)
                for index in xrange(block, (end - 1 >> self.buffer_size) + 1)
            )[offset:offset+size]
        self._flush()
        self.address += len(data)
        return data

class InputIOStream(InputStream):
    def __init__(self, input, size=None, **args):
        if not hasattr(input, "seek"):
            if size is None:
                input = InputPipe(input, self._setSize)
            else:
                input = InputPipe(input)
        elif size is None:
            try:
                input.seek(0, 2)
                size = input.tell() * 8
            except IOError, err:
                if err.errno == ESPIPE:
                    input = InputPipe(input, self._setSize)
                else:
                    charset = getTerminalCharset()
                    errmsg = unicode(str(err), charset)
                    source = args.get("source", "<inputio:%r>" % input)
                    raise InputStreamError(_("Unable to get size of %s: %s") % (source, errmsg))
        self._input = input
        InputStream.__init__(self, size=size, **args)

    def __current_size(self):
        if self._size:
            return self._size
        if self._input.size:
            return 8 * self._input.size
        return 8 * self._input.current_size
    _current_size = property(__current_size)

    def read(self, address, size):
        assert size > 0
        _size = self._size
        address, shift = divmod(address, 8)
        self._input.seek(address)
        size = (size + shift + 7) >> 3
        data = self._input.read(size)
        got = len(data)
        missing = size != got
        if missing and _size == self._size:
            raise ReadStreamError(8 * size, 8 * address, 8 * got)
        return shift, data, missing

    def file(self):
        if hasattr(self._input, "fileno"):
            from os import dup, fdopen
            new_fd = dup(self._input.fileno())
            new_file = fdopen(new_fd, "r")
            new_file.seek(0)
            return new_file
        return InputStream.file(self)


class StringInputStream(InputStream):
    def __init__(self, data, source="<string>", **args):
        self.data = data
        InputStream.__init__(self, source=source, size=8*len(data), **args)
        self._current_size = self._size

    def read(self, address, size):
        address, shift = divmod(address, 8)
        size = (size + shift + 7) >> 3
        data = self.data[address:address+size]
        got = len(data)
        if got != size:
            raise ReadStreamError(8 * size, 8 * address, 8 * got)
        return shift, data, False


class InputSubStream(InputStream):
    def __init__(self, stream, offset, size=None, source=None, **args):
        if offset is None:
            offset = 0
        if size is None and stream.size is not None:
            size = stream.size - offset
        if None < size <= 0:
            raise ValueError("InputSubStream: offset is outside input stream")
        self.stream = stream
        self._offset = offset
        if source is None:
            source = "<substream input=%s offset=%s size=%s>" % (stream.source, offset, size)
        InputStream.__init__(self, source=source, size=size, **args)
        self.stream.askSize(self)

    _current_size = property(lambda self: min(self._size, max(0, self.stream._current_size - self._offset)))

    def read(self, address, size):
        return self.stream.read(self._offset + address, size)

def InputFieldStream(field, **args):
    if not field.parent:
        return field.stream
    stream = field.parent.stream
    args["size"] = field.size
    args.setdefault("source", stream.source + field.path)
    return InputSubStream(stream, field.absolute_address, **args)


class FragmentedStream(InputStream):
    def __init__(self, field, **args):
        self.stream = field.parent.stream
        data = field.getData()
        self.fragments = [ (0, data.absolute_address, data.size) ]
        self.next = field.next
        args.setdefault("source", "%s%s" % (self.stream.source, field.path))
        InputStream.__init__(self, **args)
        if not self.next:
            self._current_size = data.size
            self._setSize()

    def _feed(self, end):
        if self._current_size < end:
            if self.checked:
                raise ReadStreamError(end - self._size, self._size)
            a, fa, fs = self.fragments[-1]
            while self.stream.sizeGe(fa + min(fs, end - a)):
                a += fs
                f = self.next
                if a >= end:
                    self._current_size = end
                    if a == end and not f:
                        self._setSize()
                    return False
                if f:
                    self.next = f.next
                    f = f.getData()
                if not f:
                    self._current_size = a
                    self._setSize()
                    return True
                fa = f.absolute_address
                fs = f.size
                self.fragments += [ (a, fa, fs) ]
            self._current_size = a + max(0, self.stream.size - fa)
            self._setSize()
            return True
        return False

    def read(self, address, size):
        assert size > 0
        missing = self._feed(address + size)
        if missing:
            size = self._size - address
            if size <= 0:
                return 0, '', True
        d = []
        i = lowerBound(self.fragments, lambda x: x[0] <= address)
        a, fa, fs = self.fragments[i-1]
        a -= address
        fa -= a
        fs += a
        s = None
        while True:
            n = min(fs, size)
            u, v, w = self.stream.read(fa, n)
            assert not w
            if s is None:
                s = u
            else:
                assert not u
            d += [ v ]
            size -= n
            if not size:
                return s, ''.join(d), missing
            a, fa, fs = self.fragments[i]
            i += 1


class ConcatStream(InputStream):
    # TODO: concatene any number of any type of stream
    def __init__(self, streams, **args):
        if len(streams) > 2 or not streams[0].checked:
            raise NotImplementedError
        self.__size0 = streams[0].size
        size1 = streams[1].askSize(self)
        if size1 is not None:
            args["size"] = self.__size0 + size1
        self.__streams = streams
        InputStream.__init__(self, **args)

    _current_size = property(lambda self: self.__size0 + self.__streams[1]._current_size)

    def read(self, address, size):
        _size = self._size
        s = self.__size0 - address
        shift, data, missing = None, '', False
        if s > 0:
            s = min(size, s)
            shift, data, w = self.__streams[0].read(address, s)
            assert not w
            a, s = 0, size - s
        else:
            a, s = -s, size
        if s:
            u, v, missing = self.__streams[1].read(a, s)
            if missing and _size == self._size:
                raise ReadStreamError(s, a)
            if shift is None:
                shift = u
            else:
                assert not u
            data += v
        return shift, data, missing
