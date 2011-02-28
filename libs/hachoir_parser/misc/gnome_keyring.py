"""
Gnome keyring parser.

Sources:
 - Gnome Keyring source code,
   function generate_file() in keyrings/gkr-keyring.c,

Author: Victor Stinner
Creation date: 2008-04-09
"""

from hachoir_core.tools import paddingSize
from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    Bit, NullBits, NullBytes,
    UInt8, UInt32, String, RawBytes, Enum,
    TimestampUnix64, CompressedField,
    SubFile)
from hachoir_core.endian import BIG_ENDIAN

try:
    import hashlib
    def sha256(data):
        hash = hashlib.new('sha256')
        hash.update(data)
        return hash.digest()
except ImportError:
    def sha256(data):
        raise ImportError("hashlib module is missing")

try:
    from Crypto.Cipher import AES
    class DeflateStream:
        def __init__(self, stream):
            hash_iterations = 1234
            password = "x" * 8
            salt = "\0" * 8
            key, iv = generate_key(password, salt, hash_iterations)
            self.cipher = AES.new(key, AES.MODE_CBC, iv)

        def __call__(self, size, data=None):
            if data is None:
                return ''
            return self.cipher.decrypt(data)

    def Deflate(field):
        CompressedField(field, DeflateStream)
        return field
except ImportError:
    def Deflate(field):
        return field

class KeyringString(FieldSet):
    def createFields(self):
        yield UInt32(self, "length")
        length = self["length"].value
        if length == 0xffffffff:
            return
        yield String(self, "text", length, charset="UTF-8")

    def createValue(self):
        if "text" in self:
            return self["text"].value
        else:
            return u''

    def createDescription(self):
        if "text" in self:
            return self["text"].value
        else:
            return u"(empty string)"

class Attribute(FieldSet):
    def createFields(self):
        yield KeyringString(self, "name")
        yield UInt32(self, "type")
        type = self["type"].value
        if type == 0:
            yield KeyringString(self, "value")
        elif type == 1:
            yield UInt32(self, "value")
        else:
            raise TypeError("Unknown attribute type (%s)" % type)

    def createDescription(self):
        return 'Attribute "%s"' % self["name"].value

class ACL(FieldSet):
    def createFields(self):
        yield UInt32(self, "types_allowed")
        yield KeyringString(self, "display_name")
        yield KeyringString(self, "pathname")
        yield KeyringString(self, "reserved[]")
        yield UInt32(self, "reserved[]")

class Item(FieldSet):
    def createFields(self):
        yield UInt32(self, "id")
        yield UInt32(self, "type")
        yield UInt32(self, "attr_count")
        for index in xrange(self["attr_count"].value):
            yield Attribute(self, "attr[]")

    def createDescription(self):
        return "Item #%s: %s attributes" % (self["id"].value, self["attr_count"].value)

class Items(FieldSet):
    def createFields(self):
        yield UInt32(self, "count")
        for index in xrange(self["count"].value):
            yield Item(self, "item[]")

class EncryptedItem(FieldSet):
    def createFields(self):
        yield KeyringString(self, "display_name")
        yield KeyringString(self, "secret")
        yield TimestampUnix64(self, "mtime")
        yield TimestampUnix64(self, "ctime")
        yield KeyringString(self, "reserved[]")
        for index in xrange(4):
            yield UInt32(self, "reserved[]")
        yield UInt32(self, "attr_count")
        for index in xrange(self["attr_count"].value):
            yield Attribute(self, "attr[]")
        yield UInt32(self, "acl_count")
        for index in xrange(self["acl_count"].value):
            yield ACL(self, "acl[]")
#        size = 8 # paddingSize((self.stream.size - self.current_size) // 8, 16)
#        if size:
#            yield NullBytes(self, "hash_padding", size, "16 bytes alignment")

class EncryptedData(Parser):
    PARSER_TAGS = {
        "id": "gnomeencryptedkeyring",
        "min_size": 16*8,
        "description": u"Gnome encrypted keyring",
    }
    endian = BIG_ENDIAN
    def validate(self):
        return True

    def createFields(self):
        yield RawBytes(self, "md5", 16)
        while True:
            size = (self.size - self.current_size) // 8
            if size < 77:
                break
            yield EncryptedItem(self, "item[]")
        size = paddingSize(self.current_size // 8, 16)
        if size:
            yield NullBytes(self, "padding_align", size)

class GnomeKeyring(Parser):
    MAGIC = "GnomeKeyring\n\r\0\n"
    PARSER_TAGS = {
        "id": "gnomekeyring",
        "category": "misc",
        "magic": ((MAGIC, 0),),
        "min_size": 47*8,
        "description": u"Gnome keyring",
    }
    CRYPTO_NAMES = {
        0: u"AEL",
    }
    HASH_NAMES = {
        0: u"MD5",
    }

    endian = BIG_ENDIAN

    def validate(self):
        if self.stream.readBytes(0, len(self.MAGIC)) != self.MAGIC:
            return u"Invalid magic string"
        return True

    def createFields(self):
        yield String(self, "magic", len(self.MAGIC), 'Magic string (%r)' % self.MAGIC, charset="ASCII")
        yield UInt8(self, "major_version")
        yield UInt8(self, "minor_version")
        yield Enum(UInt8(self, "crypto"), self.CRYPTO_NAMES)
        yield Enum(UInt8(self, "hash"), self.HASH_NAMES)
        yield KeyringString(self, "keyring_name")
        yield TimestampUnix64(self, "mtime")
        yield TimestampUnix64(self, "ctime")
        yield Bit(self, "lock_on_idle")
        yield NullBits(self, "reserved[]", 31, "Reserved for future flags")
        yield UInt32(self, "lock_timeout")
        yield UInt32(self, "hash_iterations")
        yield RawBytes(self, "salt", 8)
        yield NullBytes(self, "reserved[]", 16)
        yield Items(self, "items")
        yield UInt32(self, "encrypted_size")
        yield Deflate(SubFile(self, "encrypted", self["encrypted_size"].value, "AES128 CBC", parser_class=EncryptedData))

def generate_key(password, salt, hash_iterations):
    sha = sha256(password+salt)
    for index in xrange(hash_iterations-1):
        sha = sha256(sha)
    return sha[:16], sha[16:]

