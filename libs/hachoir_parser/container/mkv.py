#
# Matroska parser
# Author Julien Muchembled <jm AT jm10.no-ip.com>
# Created: 8 june 2006
#

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet, Link,
    MissingField, ParserError,
    Enum as _Enum, String as _String,
    Float32, Float64,
    NullBits, Bits, Bit, RawBytes, Bytes,
    Int16, GenericInteger)
from hachoir_core.endian import BIG_ENDIAN
from hachoir_core.iso639 import ISO639_2
from hachoir_core.tools import humanDatetime
from hachoir_core.text_handler import textHandler, hexadecimal
from hachoir_parser.container.ogg import XiphInt
from datetime import datetime, timedelta

class RawInt(GenericInteger):
    """
    Raw integer: have to be used in BIG_ENDIAN!
    """
    def __init__(self, parent, name, description=None):
        GenericInteger.__init__(self, parent, name, False, 8, description)
        i = GenericInteger.createValue(self)
        if i == 0:
            raise ParserError('Invalid integer length!')
        while i < 0x80:
            self._size += 8
            i <<= 1

class Unsigned(RawInt):
    def __init__(self, parent, name, description=None):
        RawInt.__init__(self, parent, name, description)

    def hasValue(self):
        return True
    def createValue(self):
        header = 1 << self._size / 8 * 7
        value = RawInt.createValue(self) - header
        if value + 1 == header:
            return None
        return value

class Signed(Unsigned):
    def createValue(self):
        header = 1 << self._size / 8 * 7 - 1
        value = RawInt.createValue(self) - 3 * header + 1
        if value == header:
            return None
        return value

def Enum(parent, enum):
    return _Enum(GenericInteger(parent, 'enum', False, parent['size'].value*8), enum)

def Bool(parent):
    return textHandler(GenericInteger(parent, 'bool', False, parent['size'].value*8),
        lambda chunk: str(chunk.value != 0))

def UInt(parent):
    return GenericInteger(parent, 'unsigned', False, parent['size'].value*8)

def SInt(parent):
    return GenericInteger(parent, 'signed', True, parent['size'].value*8)

def String(parent):
    return _String(parent, 'string', parent['size'].value, charset="ASCII")

def EnumString(parent, enum):
    return _Enum(String(parent), enum)

def Binary(parent):
    return RawBytes(parent, 'binary', parent['size'].value)

class AttachedFile(Bytes):
    def __init__(self, parent):
        Bytes.__init__(self, parent, 'file', parent['size'].value, None)
    def _getFilename(self):
        if not hasattr(self, "_filename"):
            try:
                self._filename = self["../../FileName/unicode"].value
            except MissingField:
                self._filename = None
        return self._filename
    def createDescription(self):
        filename = self._getFilename()
        if filename:
            return 'File "%s"' % filename
        return "('Filename' entry not found)"
    def _createInputStream(self, **args):
        tags = args.setdefault("tags",[])
        try:
            tags.append(("mime", self["../../FileMimeType/string"].value))
        except MissingField:
            pass
        filename = self._getFilename()
        if filename:
            tags.append(("filename", filename))
        return Bytes._createInputStream(self, **args)

def UTF8(parent):
    return _String(parent,'unicode', parent['size'].value, charset='UTF-8')

def Float(parent):
    size = parent['size'].value
    if size == 4:
        return Float32(parent, 'float')
    elif size == 8:
        return Float64(parent, 'double')
    else:
        return RawBytes(parent, 'INVALID_FLOAT', size)

TIMESTAMP_T0 = datetime(2001, 1, 1)

def dateToDatetime(value):
    return TIMESTAMP_T0 + timedelta(microseconds=value//1000)

def dateToString(field):
    return humanDatetime(dateToDatetime(field.value))

def Date(parent):
    return textHandler(GenericInteger(parent, 'date', True, parent['size'].value*8),
        dateToString)

def SeekID(parent):
    return textHandler(GenericInteger(parent, 'binary', False, parent['size'].value*8),
        lambda chunk: segment.get(chunk.value, (hexadecimal(chunk),))[0])

def CueClusterPosition(parent):
    class Cluster(Link):
        def createValue(self):
            parent = self.parent
            segment = parent['.....']
            pos = parent['unsigned'].value * 8 + segment[2].address
            return segment.getFieldByAddress(pos, feed=False)
    return Cluster(parent, 'cluster')

def CueTrackPositions(parent):
    class Block(Link):
        def createValue(self):
            parent = self.parent
            time = parent['../CueTime/unsigned'].value
            track = parent['CueTrack/unsigned'].value
            cluster = parent['CueClusterPosition/cluster'].value
            time -= cluster['Timecode/unsigned'].value
            for field in cluster:
                if field.name.startswith('BlockGroup['):
                    for path in 'Block/block', 'SimpleBlock':
                        try:
                            block = field[path]
                            if block['track'].value == track and \
                               block['timecode'].value == time:
                                return field
                        except MissingField:
                            pass
            parent.error('Cue point not found')
            return self
    return Block(parent, 'block')

class Lace(FieldSet):
    def __init__(self, parent, lacing, size):
        self.n_frames = parent['n_frames'].value
        self.createFields = ( self.parseXiph, self.parseFixed, self.parseEBML )[lacing]
        FieldSet.__init__(self, parent, 'Lace', size=size * 8)

    def parseXiph(self):
        for i in xrange(self.n_frames):
            yield XiphInt(self, 'size[]')
        for i in xrange(self.n_frames):
            yield RawBytes(self, 'frame[]', self['size['+str(i)+']'].value)
        yield RawBytes(self,'frame[]', (self._size - self.current_size) / 8)

    def parseEBML(self):
        yield Unsigned(self, 'size')
        for i in xrange(1, self.n_frames):
            yield Signed(self, 'dsize[]')
        size = self['size'].value
        yield RawBytes(self, 'frame[]', size)
        for i in xrange(self.n_frames-1):
            size += self['dsize['+str(i)+']'].value
            yield RawBytes(self, 'frame[]', size)
        yield RawBytes(self,'frame[]', (self._size - self.current_size) / 8)

    def parseFixed(self):
        n = self.n_frames + 1
        size = self._size / 8 / n
        for i in xrange(n):
            yield RawBytes(self, 'frame[]', size)

class Block(FieldSet):
    def __init__(self, parent):
        FieldSet.__init__(self, parent, 'block')
        self._size = 8 * parent['size'].value

    def lacing(self):
        return _Enum(Bits(self, 'lacing', 2), [ 'none', 'Xiph', 'fixed', 'EBML' ])

    def createFields(self):
        yield Unsigned(self, 'track')
        yield Int16(self, 'timecode')

        if self.parent._name == 'Block':
            yield NullBits(self, 'reserved[]', 4)
            yield Bit(self, 'invisible')
            yield self.lacing()
            yield NullBits(self, 'reserved[]', 1)
        elif self.parent._name == 'SimpleBlock[]':
            yield Bit(self, 'keyframe')
            yield NullBits(self, 'reserved', 3)
            yield Bit(self, 'invisible')
            yield self.lacing()
            yield Bit(self, 'discardable')
        else:
            yield NullBits(self, 'reserved', 8)
            return

        size = (self._size - self.current_size) / 8
        lacing = self['lacing'].value
        if lacing:
            yield textHandler(GenericInteger(self, 'n_frames', False, 8),
                lambda chunk: str(chunk.value+1))
            yield Lace(self, lacing - 1, size - 1)
        else:
            yield RawBytes(self,'frame', size)

ebml = {
    0x1A45DFA3: ('EBML[]', {
        0x4286: ('EBMLVersion',UInt),
        0x42F7: ('EBMLReadVersion',UInt),
        0x42F2: ('EBMLMaxIDLength',UInt),
        0x42F3: ('EBMLMaxSizeLength',UInt),
        0x4282: ('DocType',String),
        0x4287: ('DocTypeVersion',UInt),
        0x4285: ('DocTypeReadVersion',UInt)
        })
}

signature = {
    0x7E8A: ('SignatureAlgo', UInt),
    0x7E9A: ('SignatureHash', UInt),
    0x7EA5: ('SignaturePublicKey', Binary),
    0x7EB5: ('Signature', Binary),
    0x7E5B: ('SignatureElements', {
        0x7E7B: ('SignatureElementList[]', {
            0x6532: ('SignedElement[]', Binary)
            })
        })
}

chapter_atom = {
    0x73C4: ('ChapterUID', UInt),
    0x91:   ('ChapterTimeStart', UInt),
    0x92:   ('ChapterTimeEnd', UInt),
    0x98:   ('ChapterFlagHidden', Bool),
    0x4598: ('ChapterFlagEnabled', Bool),
    0x6E67: ('ChapterSegmentUID', Binary),
    0x6EBC: ('ChapterSegmentEditionUID', Binary),
    0x63C3: ('ChapterPhysicalEquiv', UInt),
    0x8F:   ('ChapterTrack', {
        0x89:   ('ChapterTrackNumber[]', UInt)
        }),
    0x80:   ('ChapterDisplay[]', {
        0x85:   ('ChapString', UTF8),
        0x437C: ('ChapLanguage[]', String),
        0x437E: ('ChapCountry[]', String)
        }),
    0x6944: ('ChapProcess[]', {
        0x6955: ('ChapProcessCodecID', UInt),
        0x450D: ('ChapProcessPrivate', Binary),
        0x6911: ('ChapProcessCommand[]', {
        0x6922: ('ChapProcessTime', UInt),
        0x6933: ('ChapProcessData', Binary)
        })
        })
}

simple_tag = {
    0x45A3: ('TagName', UTF8),
    0x447A: ('TagLanguage', String),
    0x44B4: ('TagDefault', Bool), # 0x4484
    0x4487: ('TagString', UTF8),
    0x4485: ('TagBinary', Binary)
}

segment_seek = {
    0x4DBB:     ('Seek[]', {
        0x53AB:     ('SeekID', SeekID),
        0x53AC:     ('SeekPosition', UInt)
        })
}

segment_info = {
    0x73A4:     ('SegmentUID', Binary),
    0x7384:     ('SegmentFilename', UTF8),
    0x3CB923:   ('PrevUID', Binary),
    0x3C83AB:   ('PrevFilename', UTF8),
    0x3EB923:   ('NextUID', Binary),
    0x3E83BB:   ('NextFilename', UTF8),
    0x4444:     ('SegmentFamily[]', Binary),
    0x6924:     ('ChapterTranslate[]', {
        0x69FC:     ('ChapterTranslateEditionUID[]', UInt),
        0x69BF:     ('ChapterTranslateCodec', UInt),
        0x69A5:     ('ChapterTranslateID', Binary)
        }),
    0x2AD7B1:   ('TimecodeScale', UInt),
    0x4489:     ('Duration', Float),
    0x4461:     ('DateUTC', Date),
    0x7BA9:     ('Title', UTF8),
    0x4D80:     ('MuxingApp', UTF8),
    0x5741:     ('WritingApp', UTF8)
}

segment_clusters = {
    0xE7:       ('Timecode', UInt),
    0x5854:     ('SilentTracks', {
        0x58D7:     ('SilentTrackNumber[]', UInt)
        }),
    0xA7:       ('Position', UInt),
    0xAB:       ('PrevSize', UInt),
    0xA0:       ('BlockGroup[]', {
        0xA1:       ('Block', Block),
        0xA2:       ('BlockVirtual[]', Block),
        0x75A1:     ('BlockAdditions', {
            0xA6:       ('BlockMore[]', {
                0xEE:       ('BlockAddID', UInt),
                0xA5:       ('BlockAdditional', Binary)
                })
            }),
        0x9B:       ('BlockDuration', UInt),
        0xFA:       ('ReferencePriority', UInt),
        0xFB:       ('ReferenceBlock[]', SInt),
        0xFD:       ('ReferenceVirtual', SInt),
        0xA4:       ('CodecState', Binary),
        0x8E:       ('Slices[]', {
            0xE8:       ('TimeSlice[]', {
                0xCC:       ('LaceNumber', UInt),
                0xCD:       ('FrameNumber', UInt),
                0xCB:       ('BlockAdditionID', UInt),
                0xCE:       ('Delay', UInt),
                0xCF:       ('Duration', UInt)
                })
            })
        }),
    0xA3:       ('SimpleBlock[]', Block)
}

tracks_video = {
    0x9A:       ('FlagInterlaced', Bool),
    0x53B8:     ('StereoMode', lambda parent: Enum(parent, \
        [ 'mono', 'right eye', 'left eye', 'both eyes' ])),
    0xB0:       ('PixelWidth', UInt),
    0xBA:       ('PixelHeight', UInt),
    0x54AA:     ('PixelCropBottom', UInt),
    0x54BB:     ('PixelCropTop', UInt),
    0x54CC:     ('PixelCropLeft', UInt),
    0x54DD:     ('PixelCropRight', UInt),
    0x54B0:     ('DisplayWidth', UInt),
    0x54BA:     ('DisplayHeight', UInt),
    0x54B2:     ('DisplayUnit', lambda parent: Enum(parent, \
        [ 'pixels', 'centimeters', 'inches' ])),
    0x54B3:     ('AspectRatioType', lambda parent: Enum(parent, \
        [ 'free resizing', 'keep aspect ratio', 'fixed' ])),
    0x2EB524:   ('ColourSpace', Binary),
    0x2FB523:   ('GammaValue', Float)
}

tracks_audio = {
    0xB5:       ('SamplingFrequency', Float),
    0x78B5:     ('OutputSamplingFrequency', Float),
    0x9F:       ('Channels', UInt),
    0x7D7B:     ('ChannelPositions', Binary),
    0x6264:     ('BitDepth', UInt)
}

tracks_content_encodings = {
    0x6240:     ('ContentEncoding[]', {
        0x5031:     ('ContentEncodingOrder', UInt),
        0x5032:     ('ContentEncodingScope', UInt),
        0x5033:     ('ContentEncodingType', UInt),
        0x5034:     ('ContentCompression', {
            0x4254:     ('ContentCompAlgo', UInt),
            0x4255:     ('ContentCompSettings', Binary)
            }),
        0x5035:     ('ContentEncryption', {
            0x47e1:     ('ContentEncAlgo', UInt),
            0x47e2:     ('ContentEncKeyID', Binary),
            0x47e3:     ('ContentSignature', Binary),
            0x47e4:     ('ContentSigKeyID', Binary),
            0x47e5:     ('ContentSigAlgo', UInt),
            0x47e6:     ('ContentSigHashAlgo', UInt),
            })
        })
}

segment_tracks = {
    0xAE:       ('TrackEntry[]', {
        0xD7:       ('TrackNumber', UInt),
        0x73C5:     ('TrackUID', UInt),
        0x83:       ('TrackType', lambda parent: Enum(parent, {
            0x01: 'video',
            0x02: 'audio',
            0x03: 'complex',
            0x10: 'logo',
            0x11: 'subtitle',
            0x12: 'buttons',
            0x20: 'control'
            })),
        0xB9:       ('FlagEnabled', Bool),
        0x88:       ('FlagDefault', Bool),
        0x55AA:     ('FlagForced[]', Bool),
        0x9C:       ('FlagLacing', Bool),
        0x6DE7:     ('MinCache', UInt),
        0x6DF8:     ('MaxCache', UInt),
        0x23E383:   ('DefaultDuration', UInt),
        0x23314F:   ('TrackTimecodeScale', Float),
        0x537F:     ('TrackOffset', SInt),
        0x55EE:     ('MaxBlockAdditionID', UInt),
        0x536E:     ('Name', UTF8),
        0x22B59C:   ('Language', lambda parent: EnumString(parent, ISO639_2)),
        0x86:       ('CodecID', String),
        0x63A2:     ('CodecPrivate', Binary),
        0x258688:   ('CodecName', UTF8),
        0x7446:     ('AttachmentLink', UInt),
        0x3A9697:   ('CodecSettings', UTF8),
        0x3B4040:   ('CodecInfoURL[]', String),
        0x26B240:   ('CodecDownloadURL[]', String),
        0xAA:       ('CodecDecodeAll', Bool),
        0x6FAB:     ('TrackOverlay[]', UInt),
        0x6624:     ('TrackTranslate[]', {
            0x66FC:     ('TrackTranslateEditionUID[]', UInt),
            0x66BF:     ('TrackTranslateCodec', UInt),
            0x66A5:     ('TrackTranslateTrackID', Binary)
            }),
        0xE0:       ('Video', tracks_video),
        0xE1:       ('Audio', tracks_audio),
        0x6d80:     ('ContentEncodings', tracks_content_encodings)
        })
}

segment_cues = {
    0xBB:       ('CuePoint[]', {
        0xB3:       ('CueTime', UInt),
        0xB7:       ('CueTrackPositions[]', CueTrackPositions, {
            0xF7:       ('CueTrack', UInt),
            0xF1:       ('CueClusterPosition', CueClusterPosition, UInt),
            0x5378:     ('CueBlockNumber', UInt),
            0xEA:       ('CueCodecState', UInt),
            0xDB:       ('CueReference[]', {
                0x96:       ('CueRefTime', UInt),
                0x97:       ('CueRefCluster', UInt),
                0x535F:     ('CueRefNumber', UInt),
                0xEB:       ('CueRefCodecState', UInt)
                })
            })
        })
}

segment_attachments = {
    0x61A7:     ('AttachedFile[]', {
        0x467E:     ('FileDescription', UTF8),
        0x466E:     ('FileName', UTF8),
        0x4660:     ('FileMimeType', String),
        0x465C:     ('FileData', AttachedFile),
        0x46AE:     ('FileUID', UInt),
        0x4675:     ('FileReferral', Binary)
        })
}

segment_chapters = {
    0x45B9:     ('EditionEntry[]', {
        0x45BC:     ('EditionUID', UInt),
        0x45BD:     ('EditionFlagHidden', Bool),
        0x45DB:     ('EditionFlagDefault', Bool),
        0x45DD:     ('EditionFlagOrdered', Bool),
        0xB6:       ('ChapterAtom[]', chapter_atom)
        })
}

segment_tags = {
    0x7373:     ('Tag[]', {
        0x63C0:     ('Targets', {
            0x68CA:     ('TargetTypeValue', UInt),
            0x63CA:     ('TargetType', String),
            0x63C5:     ('TrackUID[]', UInt),
            0x63C9:     ('EditionUID[]', UInt),
            0x63C4:     ('ChapterUID[]', UInt),
            0x63C6:     ('AttachmentUID[]', UInt)
            }),
        0x67C8:     ('SimpleTag[]', simple_tag)
        })
}

segment = {
    0x114D9B74: ('SeekHead[]', segment_seek),
    0x1549A966: ('Info[]', segment_info),
    0x1F43B675: ('Cluster[]', segment_clusters),
    0x1654AE6B: ('Tracks[]', segment_tracks),
    0x1C53BB6B: ('Cues', segment_cues),
    0x1941A469: ('Attachments', segment_attachments),
    0x1043A770: ('Chapters', segment_chapters),
    0x1254C367: ('Tags[]', segment_tags)
}

class EBML(FieldSet):
    def __init__(self, parent, ids):
        FieldSet.__init__(self, parent, "?[]")

        # Set name
        id = self['id'].value
        self.val = ids.get(id)
        if not self.val:
            if id == 0xBF:
                self.val = 'CRC-32[]', Binary
            elif id == 0xEC:
                self.val = 'Void[]', Binary
            elif id == 0x1B538667:
                self.val = 'SignatureSlot[]', signature
            else:
                self.val = 'Unknown[]', Binary
        self._name = self.val[0]

        # Compute size
        size = self['size']
        if size.value is not None:
            self._size = size.address + size.size + size.value * 8
        elif self._parent._parent:
            raise ParserError("Unknown length (only allowed for the last Level 0 element)")
        elif self._parent._size is not None:
            self._size = self._parent._size - self.address

    def createFields(self):
        yield RawInt(self, 'id')
        yield Unsigned(self, 'size')
        for val in self.val[1:]:
            if callable(val):
                yield val(self)
            else:
                while not self.eof:
                    yield EBML(self, val)

class MkvFile(Parser):
    EBML_SIGNATURE = 0x1A45DFA3
    PARSER_TAGS = {
        "id": "matroska",
        "category": "container",
        "file_ext": ("mka", "mkv", "webm"),
        "mime": (
            u"video/x-matroska",
            u"audio/x-matroska",
            u"video/webm",
            u"audio/webm"),
        "min_size": 5*8,
        "magic": (("\x1A\x45\xDF\xA3", 0),),
        "description": "Matroska multimedia container"
    }
    endian = BIG_ENDIAN

    def _getDoctype(self):
        return self[0]['DocType/string'].value

    def validate(self):
        if self.stream.readBits(0, 32, self.endian) != self.EBML_SIGNATURE:
            return False
        try:
            first = self[0]
        except ParserError:
            return False
        if None < self._size < first._size:
            return "First chunk size is invalid"
        if self._getDoctype() not in ('matroska', 'webm'):
            return "Stream isn't a matroska document."
        return True

    def createFields(self):
        hdr = EBML(self, ebml)
        yield hdr

        while not self.eof:
            yield EBML(self, { 0x18538067: ('Segment[]', segment) })

    def createContentSize(self):
        field = self["Segment[0]/size"]
        return field.absolute_address + field.value * 8 + field.size

    def createDescription(self):
        if self._getDoctype() == 'webm':
            return 'WebM video'
        else:
            return 'Matroska video'

    def createMimeType(self):
        if self._getDoctype() == 'webm':
            return u"video/webm"
        else:
            return u"video/x-matroska"

