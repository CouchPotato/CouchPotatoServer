"""
3D Studio Max file (.3ds) parser.
Author: Victor Stinner
"""

from hachoir_parser import Parser
from hachoir_core.field import (StaticFieldSet, FieldSet,
    UInt16, UInt32, RawBytes, Enum, CString)
from hachoir_parser.image.common import RGB
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_parser.misc.common import Vertex, MapUV

def readObject(parent):
    yield CString(parent, "name", "Object name")
    size = parent["size"].value * 8
    while parent.current_size < size:
        yield Chunk(parent, "chunk[]")

def readTextureFilename(parent):
    yield CString(parent, "filename", "Texture filename")

def readVersion(parent):
    yield UInt32(parent, "version", "3DS file format version")

def readMaterialName(parent):
    yield CString(parent, "name", "Material name")

class Polygon(StaticFieldSet):
    format = (
        (UInt16, "a", "Vertex A"),
        (UInt16, "b", "Vertex B"),
        (UInt16, "c", "Vertex C"),
        (UInt16, "flags", "Flags"))

def readMapList(parent):
    yield UInt16(parent, "count", "Map count")
    for index in xrange(parent["count"].value):
        yield MapUV(parent, "map_uv[]", "Mapping UV")

def readColor(parent):
    yield RGB(parent, "color")

def readVertexList(parent):
    yield UInt16(parent, "count", "Vertex count")
    for index in range(0, parent["count"].value):
        yield Vertex(parent, "vertex[]", "Vertex")

def readPolygonList(parent):
    count = UInt16(parent, "count", "Vertex count")
    yield count
    for i in range(0, count.value):
        yield Polygon(parent, "polygon[]")
    size = parent["size"].value * 8
    while parent.current_size < size:
        yield Chunk(parent, "chunk[]")

class Chunk(FieldSet):
    # List of chunk type name
    type_name = {
        0x0011: "Color",
        0x4D4D: "Main chunk",
        0x0002: "File version",
        0x3D3D: "Materials and objects",
        0x4000: "Object",
        0x4100: "Mesh (triangular)",
        0x4110: "Vertices list",
        0x4120: "Polygon (faces) list",
        0x4140: "Map UV list",
        0x4130: "Object material",
        0xAFFF: "New material",
        0xA000: "Material name",
        0xA010: "Material ambient",
        0xA020: "Material diffuse",
        0xA030: "Texture specular",
        0xA200: "Texture",
        0xA300: "Texture filename",

        # Key frames
        0xB000: "Keyframes",
        0xB002: "Object node tag",
        0xB006: "Light target node tag",
        0xB007: "Spot light node tag",
        0xB00A: "Keyframes header",
        0xB009: "Keyframe current time",
        0xB030: "Node identifier",
        0xB010: "Node header",
        0x7001: "Viewport layout"
    }

    chunk_id_by_type = {
        0x4d4d: "main",
        0x0002: "version",
        0x3d3d: "obj_mat",
        0xb000: "keyframes",
        0xafff: "material[]",
        0x4000: "object[]",
        0x4110: "vertices_list",
        0x4120: "polygon_list",
        0x4140: "mapuv_list",
        0x4100: "mesh"
    }

    # List of chunks which contains other chunks
    sub_chunks = \
        (0x4D4D, 0x4100, 0x3D3D, 0xAFFF, 0xA200,
         0xB002, 0xB006, 0xB007,
         0xA010, 0xA030, 0xA020, 0xB000)

    # List of chunk type handlers
    handlers = {
        0xA000: readMaterialName,
        0x4000: readObject,
        0xA300: readTextureFilename,
        0x0011: readColor,
        0x0002: readVersion,
        0x4110: readVertexList,
        0x4120: readPolygonList,
        0x4140: readMapList
    }

    def __init__(self, *args):
        FieldSet.__init__(self, *args)

        # Set description
        self._description = "Chunk: %s" % self["type"].display

        # Set name based on type field
        type = self["type"].value
        if type in Chunk.chunk_id_by_type:
            self._name = Chunk.chunk_id_by_type[type]
        else:
            self._name = "chunk_%04x" % type

        # Guess chunk size
        self._size = self["size"].value * 8

    def createFields(self):
        yield Enum(textHandler(UInt16(self, "type", "Chunk type"), hexadecimal), Chunk.type_name)
        yield UInt32(self, "size", "Chunk size (in bytes)")
        content_size = self["size"].value - 6
        if content_size == 0:
            return
        type = self["type"].value
        if type in Chunk.sub_chunks:
            while self.current_size < self.size:
                yield Chunk(self, "chunk[]")
        else:
            if type in Chunk.handlers:
                fields = Chunk.handlers[type] (self)
                for field in fields:
                    yield field
            else:
                yield RawBytes(self, "data", content_size)

class File3ds(Parser):
    endian = LITTLE_ENDIAN
    PARSER_TAGS = {
        "id": "3ds",
        "category": "misc",
        "file_ext": ("3ds",),
        "mime": (u"image/x-3ds",),
        "min_size": 16*8,
        "description": "3D Studio Max model"
    }

    def validate(self):
        if self.stream.readBytes(0, 2) != "MM":
            return "Wrong signature"
        if self["main/version/version"].value not in (2, 3):
            return "Unknown format version"
        return True

    def createFields(self):
        while not self.eof:
            yield Chunk(self, "chunk[]")

