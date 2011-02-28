from hachoir_core.field import CompressedField

try:
    from zlib import decompressobj, MAX_WBITS

    class DeflateStream:
        def __init__(self, stream, wbits=None):
            if wbits:
                self.gzip = decompressobj(-MAX_WBITS)
            else:
                self.gzip = decompressobj()

        def __call__(self, size, data=None):
            if data is None:
                data = ''
            return self.gzip.decompress(self.gzip.unconsumed_tail+data, size)

    class DeflateStreamWbits(DeflateStream):
        def __init__(self, stream):
            DeflateStream.__init__(self, stream, True)

    def Deflate(field, wbits=True):
        if wbits:
            CompressedField(field, DeflateStreamWbits)
        else:
            CompressedField(field, DeflateStream)
        return field
    has_deflate = True
except ImportError:
    def Deflate(field, wbits=True):
        return field
    has_deflate = False

