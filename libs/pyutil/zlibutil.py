#  Copyright (c) 2002-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

"""
Making your zlib experience that much nicer!

Most importantly, this offers protection from "zlib bomb" attacks, where the
original data was maximally compressable, and a naive use of zlib would
consume all of your RAM while trying to decompress it.
"""

import exceptions, string, zlib

from humanreadable import hr
from pyutil.assertutil import precondition

class DecompressError(exceptions.StandardError, zlib.error): pass
class UnsafeDecompressError(DecompressError): pass # This means it would take more memory to decompress than we can spare.
class TooBigError(DecompressError): pass # This means the resulting uncompressed text would exceed the maximum allowed length.
class ZlibError(DecompressError): pass # internal error, probably due to the input not being zlib compressed text

# The smallest limit that you can impose on zlib decompression and still have
# a chance of succeeding at decompression.

# constant memory overhead of zlib (76 KB), plus minbite (128 bytes) times
# maxexpansion (1032) times buffer-copying duplication (2), plus 2063 so as
# to reach the ceiling of div (2*1032)

MINMAXMEM=76*2**10 + 128 * 1032 * 2 + 2063 - 1

# You should really specify a maxmem which is much higher than MINMAXMEM. If
# maxmem=MINMAXMEM, we will be reduced to decompressing the input in
# 128-byte bites, and furthermore unless the decompressed text is quite small,
# we will be forced to give up and spuriously raise UnsafeDecompressError!
# You really ought to pass a maxmem argument equal to the maximum possible
# memory that your app should ever allocate (for a short-term use).
# I typically set it to 65 MB.

def decompress(zbuf, maxlen=(65 * (2**20)), maxmem=(65 * (2**20))):
    """
    Decompress zbuf so that it decompresses to <= maxlen bytes, while using
    <= maxmem memory, or else raise an exception.  If zbuf contains
    uncompressed data an exception will be raised.

   This function guards against memory allocation attacks.

    @param maxlen the resulting text must not be greater than this
    @param maxmem the execution of this function must not use more than this
        amount of memory in bytes;  The higher this number is (optimally
        1032 * maxlen, or even greater), the faster this function can
        complete.  (Actually I don't fully understand the workings of zlib, so
        this function might use a *little* more than this memory, but not a
        lot more.)  (Also, this function will raise an exception if the amount
        of memory required even *approaches* maxmem.  Another reason to make
        it large.)  (Hence the default value which would seem to be
        exceedingly large until you realize that it means you can decompress
        64 KB chunks of compressiontext at a bite.)
    """
    assert isinstance(maxlen, (int, long,)) and maxlen > 0, "maxlen is required to be a real maxlen, geez!"
    assert isinstance(maxmem, (int, long,)) and maxmem > 0, "maxmem is required to be a real maxmem, geez!"
    assert maxlen <= maxmem, "maxlen is required to be <= maxmem.  All data that is included in the return value is counted against maxmem as well as against maxlen, so it is impossible to return a result bigger than maxmem, even if maxlen is bigger than maxmem.  See decompress_to_spool() if you want to spool a large text out while limiting the amount of memory used during the process."

    lenzbuf = len(zbuf)
    offset = 0
    decomplen = 0
    availmem = maxmem - (76 * 2**10) # zlib can take around 76 KB RAM to do decompression
    availmem = availmem / 2 # generating the result string from the intermediate strings will require using the same amount of memory again, briefly.  If you care about this kind of thing, then let's rewrite this module in C.

    decompstrlist = []

    decomp = zlib.decompressobj()
    while offset < lenzbuf:
        # How much compressedtext can we safely attempt to decompress now without going over `maxmem'?  zlib docs say that theoretical maximum for the zlib format would be 1032:1.
        lencompbite = availmem / 1032 # XXX TODO: The biggest compression ratio zlib can have for whole files is 1032:1.  Unfortunately I don't know if small chunks of compressiontext *within* a file can expand to more than that.  I'll assume not...  --Zooko 2001-05-12
        if lencompbite < 128:
            # If we can't safely attempt even a few bytes of compression text, let us give up.  Either `maxmem' was too small or this compressiontext is actually a decompression bomb.
            raise UnsafeDecompressError, "used up roughly maxmem memory. maxmem: %s, len(zbuf): %s, offset: %s, decomplen: %s, lencompbite: %s" % tuple(map(hr, [maxmem, len(zbuf), offset, decomplen, lencompbite,]))
        # I wish the following were a local function like this:
        # def proc_decomp_bite(tmpstr, lencompbite=0, decomplen=decomplen, maxlen=maxlen, availmem=availmem, decompstrlist=decompstrlist, offset=offset, zbuf=zbuf):
        # ...but we can't conveniently and efficiently update the integer variables like offset in the outer scope.  Oh well.  --Zooko 2003-06-26
        try:
            if (offset == 0) and (lencompbite >= lenzbuf):
                tmpstr = decomp.decompress(zbuf)
            else:
                tmpstr = decomp.decompress(zbuf[offset:offset+lencompbite])
        except zlib.error, le:
            raise ZlibError, (offset, lencompbite, decomplen, hr(le), )

        lentmpstr = len(tmpstr)
        decomplen = decomplen + lentmpstr
        if decomplen > maxlen:
            raise TooBigError, "length of resulting data > maxlen. maxlen: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxlen, len(zbuf), offset, decomplen,]))
        availmem = availmem - lentmpstr
        offset = offset + lencompbite
        decompstrlist.append(tmpstr)
        tmpstr = ''

    try:
        tmpstr = decomp.flush()
    except zlib.error, le:
        raise ZlibError, (offset, lencompbite, decomplen, le, )

    lentmpstr = len(tmpstr)
    decomplen = decomplen + lentmpstr
    if decomplen > maxlen:
        raise TooBigError, "length of resulting data > maxlen. maxlen: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxlen, len(zbuf), offset, decomplen,]))
    availmem = availmem - lentmpstr
    offset = offset + lencompbite
    if lentmpstr > 0:
        decompstrlist.append(tmpstr)
        tmpstr = ''

    if len(decompstrlist) > 0:
        return string.join(decompstrlist, '')
    else:
        return decompstrlist[0]

def decompress_to_fileobj(zbuf, fileobj, maxlen=(65 * (2**20)), maxmem=(65 * (2**20))):
    """
    Decompress zbuf so that it decompresses to <= maxlen bytes, while using
    <= maxmem memory, or else raise an exception.  If zbuf contains
    uncompressed data an exception will be raised.

    This function guards against memory allocation attacks.

    Note that this assumes that data written to fileobj still occupies memory,
    so such data counts against maxmem as well as against maxlen.

    @param maxlen the resulting text must not be greater than this
    @param maxmem the execution of this function must not use more than this
        amount of memory in bytes;  The higher this number is (optimally
        1032 * maxlen, or even greater), the faster this function can
        complete.  (Actually I don't fully understand the workings of zlib, so
        this function might use a *little* more than this memory, but not a
        lot more.)  (Also, this function will raise an exception if the amount
        of memory required even *approaches* maxmem.  Another reason to make
        it large.)  (Hence the default value which would seem to be
        exceedingly large until you realize that it means you can decompress
        64 KB chunks of compressiontext at a bite.)
    @param fileobj a file object to which the decompressed text will be written
    """
    precondition(hasattr(fileobj, 'write') and callable(fileobj.write), "fileobj is required to have a write() method.", fileobj=fileobj)
    precondition(isinstance(maxlen, (int, long,)) and maxlen > 0, "maxlen is required to be a real maxlen, geez!", maxlen=maxlen)
    precondition(isinstance(maxmem, (int, long,)) and maxmem > 0, "maxmem is required to be a real maxmem, geez!", maxmem=maxmem)
    precondition(maxlen <= maxmem, "maxlen is required to be <= maxmem.  All data that is written out to fileobj is counted against maxmem as well as against maxlen, so it is impossible to return a result bigger than maxmem, even if maxlen is bigger than maxmem.  See decompress_to_spool() if you want to spool a large text out while limiting the amount of memory used during the process.", maxlen=maxlen, maxmem=maxmem)

    lenzbuf = len(zbuf)
    offset = 0
    decomplen = 0
    availmem = maxmem - (76 * 2**10) # zlib can take around 76 KB RAM to do decompression

    decomp = zlib.decompressobj()
    while offset < lenzbuf:
        # How much compressedtext can we safely attempt to decompress now without going over maxmem?  zlib docs say that theoretical maximum for the zlib format would be 1032:1.
        lencompbite = availmem / 1032 # XXX TODO: The biggest compression ratio zlib can have for whole files is 1032:1.  Unfortunately I don't know if small chunks of compressiontext *within* a file can expand to more than that.  I'll assume not...  --Zooko 2001-05-12
        if lencompbite < 128:
            # If we can't safely attempt even a few bytes of compression text, let us give up.  Either maxmem was too small or this compressiontext is actually a decompression bomb.
            raise UnsafeDecompressError, "used up roughly maxmem memory. maxmem: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxmem, len(zbuf), offset, decomplen,]))
        # I wish the following were a local function like this:
        # def proc_decomp_bite(tmpstr, lencompbite=0, decomplen=decomplen, maxlen=maxlen, availmem=availmem, decompstrlist=decompstrlist, offset=offset, zbuf=zbuf):
        # ...but we can't conveniently and efficiently update the integer variables like offset in the outer scope.  Oh well.  --Zooko 2003-06-26
        try:
            if (offset == 0) and (lencompbite >= lenzbuf):
                tmpstr = decomp.decompress(zbuf)
            else:
                tmpstr = decomp.decompress(zbuf[offset:offset+lencompbite])
        except zlib.error, le:
            raise ZlibError, (offset, lencompbite, decomplen, le, )
        lentmpstr = len(tmpstr)
        decomplen = decomplen + lentmpstr
        if decomplen > maxlen:
            raise TooBigError, "length of resulting data > maxlen. maxlen: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxlen, len(zbuf), offset, decomplen,]))
        availmem = availmem - lentmpstr
        offset = offset + lencompbite
        fileobj.write(tmpstr)
        tmpstr = ''

    try:
        tmpstr = decomp.flush()
    except zlib.error, le:
        raise ZlibError, (offset, lencompbite, decomplen, le, )
    lentmpstr = len(tmpstr)
    decomplen = decomplen + lentmpstr
    if decomplen > maxlen:
        raise TooBigError, "length of resulting data > maxlen. maxlen: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxlen, len(zbuf), offset, decomplen,]))
    availmem = availmem - lentmpstr
    offset = offset + lencompbite
    fileobj.write(tmpstr)
    tmpstr = ''

def decompress_to_spool(zbuf, fileobj, maxlen=(65 * (2**20)), maxmem=(65 * (2**20))):
    """
    Decompress zbuf so that it decompresses to <= maxlen bytes, while using
    <= maxmem memory, or else raise an exception.  If zbuf contains
    uncompressed data an exception will be raised.

    This function guards against memory allocation attacks.

    Note that this assumes that data written to fileobj does *not* continue to
    occupy memory, so such data doesn't count against maxmem, although of
    course it still counts against maxlen.

    @param maxlen the resulting text must not be greater than this
    @param maxmem the execution of this function must not use more than this
        amount of memory in bytes;  The higher this number is (optimally
        1032 * maxlen, or even greater), the faster this function can
        complete.  (Actually I don't fully understand the workings of zlib, so
        this function might use a *little* more than this memory, but not a
        lot more.)  (Also, this function will raise an exception if the amount
        of memory required even *approaches* maxmem.  Another reason to make
        it large.)  (Hence the default value which would seem to be
        exceedingly large until you realize that it means you can decompress
        64 KB chunks of compressiontext at a bite.)
    @param fileobj the decompressed text will be written to it
    """
    precondition(hasattr(fileobj, 'write') and callable(fileobj.write), "fileobj is required to have a write() method.", fileobj=fileobj)
    precondition(isinstance(maxlen, (int, long,)) and maxlen > 0, "maxlen is required to be a real maxlen, geez!", maxlen=maxlen)
    precondition(isinstance(maxmem, (int, long,)) and maxmem > 0, "maxmem is required to be a real maxmem, geez!", maxmem=maxmem)

    tmpstr = ''
    lenzbuf = len(zbuf)
    offset = 0
    decomplen = 0
    availmem = maxmem - (76 * 2**10) # zlib can take around 76 KB RAM to do decompression

    decomp = zlib.decompressobj()
    while offset < lenzbuf:
        # How much compressedtext can we safely attempt to decompress now without going over `maxmem'?  zlib docs say that theoretical maximum for the zlib format would be 1032:1.
        lencompbite = availmem / 1032 # XXX TODO: The biggest compression ratio zlib can have for whole files is 1032:1.  Unfortunately I don't know if small chunks of compressiontext *within* a file can expand to more than that.  I'll assume not...  --Zooko 2001-05-12
        if lencompbite < 128:
            # If we can't safely attempt even a few bytes of compression text, let us give up.  Either `maxmem' was too small or this compressiontext is actually a decompression bomb.
            raise UnsafeDecompressError, "used up roughly `maxmem' memory. maxmem: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxmem, len(zbuf), offset, decomplen,]))
        # I wish the following were a local function like this:
        # def proc_decomp_bite(tmpstr, lencompbite=0, decomplen=decomplen, maxlen=maxlen, availmem=availmem, decompstrlist=decompstrlist, offset=offset, zbuf=zbuf):
        # ...but we can't conveniently and efficiently update the integer variables like offset in the outer scope.  Oh well.  --Zooko 2003-06-26
        try:
            if (offset == 0) and (lencompbite >= lenzbuf):
                tmpstr = decomp.decompress(zbuf)
            else:
                tmpstr = decomp.decompress(zbuf[offset:offset+lencompbite])
        except zlib.error, le:
            raise ZlibError, (offset, lencompbite, decomplen, le, )
        lentmpstr = len(tmpstr)
        decomplen = decomplen + lentmpstr
        if decomplen > maxlen:
            raise TooBigError, "length of resulting data > `maxlen'. maxlen: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxlen, len(zbuf), offset, decomplen,]))
        offset = offset + lencompbite
        fileobj.write(tmpstr)
        tmpstr = ''

    try:
        tmpstr = decomp.flush()
    except zlib.error, le:
        raise ZlibError, (offset, lencompbite, decomplen, le, )
    lentmpstr = len(tmpstr)
    decomplen = decomplen + lentmpstr
    if decomplen > maxlen:
        raise TooBigError, "length of resulting data > `maxlen'. maxlen: %s, len(zbuf): %s, offset: %s, decomplen: %s" % tuple(map(hr, [maxlen, len(zbuf), offset, decomplen,]))
    offset = offset + lencompbite
    fileobj.write(tmpstr)
    tmpstr = ''
