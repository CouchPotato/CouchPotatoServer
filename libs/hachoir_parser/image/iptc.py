"""
IPTC metadata parser (can be found in a JPEG picture for example)

Sources:
- Image-MetaData Perl module:
  http://www.annocpan.org/~BETTELLI/Image-MetaData-JPEG-0.15/...
  ...lib/Image/MetaData/JPEG/TagLists.pod
- IPTC tag name and description:
  http://peccatte.karefil.com/software/IPTCTableau.pdf

Author: Victor Stinner
"""

from hachoir_core.field import (FieldSet, ParserError,
    UInt8, UInt16, String, RawBytes, NullBytes)
from hachoir_core.text_handler import textHandler, hexadecimal

def IPTC_String(parent, name, desc=None):
    # Charset may be utf-8, ISO-8859-1, or ...
    return String(parent, name, parent["size"].value, desc,
        strip=" ")

dataset1 = {
}
dataset2 = {
      0: ("record_version", "Record version (2 for JPEG)", UInt16),
      5: ("obj_name", "Object name", None),
      7: ("edit_stat", "Edit status", None),
     10: ("urgency", "Urgency", UInt8),
     15: ("category[]", "Category", None),
     22: ("fixture", "Fixture identifier", IPTC_String),
     25: ("keyword[]", "Keywords", IPTC_String),
     30: ("release_date", "Release date", IPTC_String),
     35: ("release_time", "Release time", IPTC_String),
     40: ("instruction", "Special instructions", IPTC_String),
     55: ("date_created", "Date created", IPTC_String),
     60: ("time_created", "Time created (ISO 8601)", IPTC_String),
     65: ("originating_prog", "Originating program", IPTC_String),
     70: ("prog_ver", "Program version", IPTC_String),
     80: ("author", "By-line (Author)", IPTC_String),
     85: ("author_job", "By-line (Author precision)", IPTC_String),
     90: ("city", "City", IPTC_String),
     95: ("state", "Province / State", IPTC_String),
    100: ("country_code", "Country / Primary location code", IPTC_String),
    101: ("country_name", "Country / Primary location name", IPTC_String),
    103: ("trans_ref", "Original transmission reference", IPTC_String),
    105: ("headline", "Headline", IPTC_String),
    110: ("credit", "Credit", IPTC_String),
    115: ("source", "Source", IPTC_String),
    116: ("copyright", "Copyright notice", IPTC_String),
    120: ("caption", "Caption/Abstract", IPTC_String),
    122: ("writer", "Writer/editor", IPTC_String),
    231: ("history[]", "Document history (timestamp)", IPTC_String)
}
datasets = {1: dataset1, 2: dataset2}

class IPTC_Size(FieldSet):
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        value = 0
        for field in self:
            value <<= 15
            value  += (field.value & 0x7fff)
        self.createValue = lambda: value

    def createFields(self):
        while True:
            field = UInt16(self, "value[]")
            yield field
            if field.value < 0x8000:
                break

class IPTC_Chunk(FieldSet):
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        number = self["dataset_nb"].value
        self.dataset_info = None
        if number in datasets:
            tag = self["tag"].value
            if tag in datasets[number]:
                self.dataset_info = datasets[number][tag]
                self._name = self.dataset_info[0]
                self._description = self.dataset_info[1]
        size_chunk = self["size"]
        self._size = 3*8 + size_chunk.size + size_chunk.value*8

    def createFields(self):
        yield textHandler(UInt8(self, "signature", "IPTC signature (0x1c)"), hexadecimal)
        if self["signature"].value != 0x1C:
            raise ParserError("Wrong IPTC signature")
        yield textHandler(UInt8(self, "dataset_nb", "Dataset number"), hexadecimal)
        yield UInt8(self, "tag", "Tag")
        yield IPTC_Size(self, "size", "Content size")

        size = self["size"].value
        if 0 < size:
            if self.dataset_info:
                cls = self.dataset_info[2]
            else:
                cls = None
            if cls:
                yield cls(self, "content")
            else:
                yield RawBytes(self, "content", size)

class IPTC(FieldSet):
    def createFields(self):
        while 5 <= (self._size - self.current_size)/8:
            yield IPTC_Chunk(self, "chunk[]")
        size = (self._size - self.current_size) / 8
        if 0 < size:
            yield NullBytes(self, "padding", size)

