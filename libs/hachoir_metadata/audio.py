from hachoir_metadata.metadata import (registerExtractor,
    Metadata, RootMetadata, MultipleMetadata)
from hachoir_parser.audio import AuFile, MpegAudioFile, RealAudioFile, AiffFile, FlacParser
from hachoir_parser.container import OggFile, RealMediaFile
from hachoir_core.i18n import _
from hachoir_core.tools import makePrintable, timedelta2seconds, humanBitRate
from datetime import timedelta
from hachoir_metadata.metadata_item import QUALITY_FAST, QUALITY_NORMAL, QUALITY_BEST
from hachoir_metadata.safe import fault_tolerant, getValue

def computeComprRate(meta, size):
    if not meta.has("duration") \
    or not meta.has("sample_rate") \
    or not meta.has("bits_per_sample") \
    or not meta.has("nb_channel") \
    or not size:
        return
    orig_size = timedelta2seconds(meta.get("duration")) * meta.get('sample_rate') * meta.get('bits_per_sample') * meta.get('nb_channel')
    meta.compr_rate = float(orig_size) / size

def computeBitRate(meta):
    if not meta.has("bits_per_sample") \
    or not meta.has("nb_channel") \
    or not meta.has("sample_rate"):
        return
    meta.bit_rate = meta.get('bits_per_sample') * meta.get('nb_channel') * meta.get('sample_rate')

VORBIS_KEY_TO_ATTR = {
    "ARTIST": "artist",
    "ALBUM": "album",
    "TRACKNUMBER": "track_number",
    "TRACKTOTAL": "track_total",
    "ENCODER": "producer",
    "TITLE": "title",
    "LOCATION": "location",
    "DATE": "creation_date",
    "ORGANIZATION": "organization",
    "GENRE": "music_genre",
    "": "comment",
    "COMPOSER": "music_composer",
    "DESCRIPTION": "comment",
    "COMMENT": "comment",
    "WWW": "url",
    "WOAF": "url",
    "LICENSE": "copyright",
}

@fault_tolerant
def readVorbisComment(metadata, comment):
    metadata.producer = getValue(comment, "vendor")
    for item in comment.array("metadata"):
        if "=" in item.value:
            key, value = item.value.split("=", 1)
            key = key.upper()
            if key in VORBIS_KEY_TO_ATTR:
                key = VORBIS_KEY_TO_ATTR[key]
                setattr(metadata, key, value)
            elif value:
                metadata.warning("Skip Vorbis comment %s: %s" % (key, value))

class OggMetadata(MultipleMetadata):
    def extract(self, ogg):
        granule_quotient = None
        for index, page in enumerate(ogg.array("page")):
            if "segments" not in page:
                continue
            page = page["segments"]
            if "vorbis_hdr" in page:
                meta = Metadata(self)
                self.vorbisHeader(page["vorbis_hdr"], meta)
                self.addGroup("audio[]", meta, "Audio")
                if not granule_quotient and meta.has("sample_rate"):
                    granule_quotient = meta.get('sample_rate')
            if "theora_hdr" in page:
                meta = Metadata(self)
                self.theoraHeader(page["theora_hdr"], meta)
                self.addGroup("video[]", meta, "Video")
            if "video_hdr" in page:
                meta = Metadata(self)
                self.videoHeader(page["video_hdr"], meta)
                self.addGroup("video[]", meta, "Video")
                if not granule_quotient and meta.has("frame_rate"):
                    granule_quotient = meta.get('frame_rate')
            if "comment" in page:
                readVorbisComment(self, page["comment"])
            if 3 <= index:
                # Only process pages 0..3
                break

        # Compute duration
        if granule_quotient and QUALITY_NORMAL <= self.quality:
            page = ogg.createLastPage()
            if page and "abs_granule_pos" in page:
                try:
                    self.duration = timedelta(seconds=float(page["abs_granule_pos"].value) / granule_quotient)
                except OverflowError:
                    pass

    def videoHeader(self, header, meta):
        meta.compression = header["fourcc"].display
        meta.width = header["width"].value
        meta.height = header["height"].value
        meta.bits_per_pixel = header["bits_per_sample"].value
        if header["time_unit"].value:
            meta.frame_rate = 10000000.0 / header["time_unit"].value

    def theoraHeader(self, header, meta):
        meta.compression = "Theora"
        meta.format_version = "Theora version %u.%u (revision %u)" % (\
            header["version_major"].value,
            header["version_minor"].value,
            header["version_revision"].value)
        meta.width = header["frame_width"].value
        meta.height = header["frame_height"].value
        if header["fps_den"].value:
            meta.frame_rate = float(header["fps_num"].value) / header["fps_den"].value
        if header["aspect_ratio_den"].value:
            meta.aspect_ratio = float(header["aspect_ratio_num"].value) / header["aspect_ratio_den"].value
        meta.pixel_format = header["pixel_format"].display
        meta.comment = "Quality: %s" % header["quality"].value

    def vorbisHeader(self, header, meta):
        meta.compression = u"Vorbis"
        meta.sample_rate = header["audio_sample_rate"].value
        meta.nb_channel = header["audio_channels"].value
        meta.format_version = u"Vorbis version %s" % header["vorbis_version"].value
        meta.bit_rate = header["bitrate_nominal"].value

class AuMetadata(RootMetadata):
    def extract(self, audio):
        self.sample_rate = audio["sample_rate"].value
        self.nb_channel = audio["channels"].value
        self.compression = audio["codec"].display
        if "info" in audio:
            self.comment = audio["info"].value
        self.bits_per_sample = audio.getBitsPerSample()
        computeBitRate(self)
        if "audio_data" in audio:
            if self.has("bit_rate"):
                self.duration = timedelta(seconds=float(audio["audio_data"].size) / self.get('bit_rate'))
            computeComprRate(self, audio["audio_data"].size)

class RealAudioMetadata(RootMetadata):
    FOURCC_TO_BITRATE = {
        u"28_8": 15200, # 28.8 kbit/sec (audio bit rate: 15.2 kbit/s)
        u"14_4": 8000,  # 14.4 kbit/sec
        u"lpcJ": 8000,  # 14.4 kbit/sec
    }

    def extract(self, real):
        version = real["version"].value
        if "metadata" in real:
            self.useMetadata(real["metadata"])
        self.useRoot(real)
        self.format_version = "Real audio version %s" % version
        if version == 3:
            size = getValue(real, "data_size")
        elif "filesize" in real and "headersize" in real:
            size = (real["filesize"].value + 40) - (real["headersize"].value + 16)
        else:
            size = None
        if size:
            size *= 8
            if self.has("bit_rate"):
                sec = float(size) / self.get('bit_rate')
                self.duration = timedelta(seconds=sec)
            computeComprRate(self, size)

    @fault_tolerant
    def useMetadata(self, info):
        self.title = info["title"].value
        self.author = info["author"].value
        self.copyright = info["copyright"].value
        self.comment = info["comment"].value

    @fault_tolerant
    def useRoot(self, real):
        self.bits_per_sample = 16   # FIXME: Is that correct?
        if real["version"].value != 3:
            self.sample_rate = real["sample_rate"].value
            self.nb_channel = real["channels"].value
        else:
            self.sample_rate = 8000
            self.nb_channel = 1
        fourcc = getValue(real, "FourCC")
        if fourcc:
            self.compression = fourcc
            try:
                self.bit_rate = self.FOURCC_TO_BITRATE[fourcc]
            except LookupError:
                pass

class RealMediaMetadata(MultipleMetadata):
    KEY_TO_ATTR = {
        "generated by": "producer",
        "creation date": "creation_date",
        "modification date": "last_modification",
        "description": "comment",
    }

    def extract(self, media):
        if "file_prop" in media:
            self.useFileProp(media["file_prop"])
        if "content_desc" in media:
            self.useContentDesc(media["content_desc"])
        for index, stream in enumerate(media.array("stream_prop")):
            self.useStreamProp(stream, index)

    @fault_tolerant
    def useFileInfoProp(self, prop):
        key = prop["name"].value.lower()
        value = prop["value"].value
        if key in self.KEY_TO_ATTR:
            setattr(self, self.KEY_TO_ATTR[key], value)
        elif value:
            self.warning("Skip %s: %s" % (prop["name"].value, value))

    @fault_tolerant
    def useFileProp(self, prop):
        self.bit_rate = prop["avg_bit_rate"].value
        self.duration = timedelta(milliseconds=prop["duration"].value)

    @fault_tolerant
    def useContentDesc(self, content):
        self.title = content["title"].value
        self.author = content["author"].value
        self.copyright = content["copyright"].value
        self.comment = content["comment"].value

    @fault_tolerant
    def useStreamProp(self, stream, index):
        meta = Metadata(self)
        meta.comment = "Start: %s" % stream["stream_start"].value
        if getValue(stream, "mime_type") == "logical-fileinfo":
            for prop in stream.array("file_info/prop"):
                self.useFileInfoProp(prop)
        else:
            meta.bit_rate = stream["avg_bit_rate"].value
            meta.duration = timedelta(milliseconds=stream["duration"].value)
            meta.mime_type = getValue(stream, "mime_type")
        meta.title = getValue(stream, "desc")
        self.addGroup("stream[%u]" % index, meta, "Stream #%u" % (1+index))

class MpegAudioMetadata(RootMetadata):
    TAG_TO_KEY = {
        # ID3 version 2.2
        "TP1": "author",
        "COM": "comment",
        "TEN": "producer",
        "TRK": "track_number",
        "TAL": "album",
        "TT2": "title",
        "TYE": "creation_date",
        "TCO": "music_genre",

        # ID3 version 2.3+
        "TPE1": "author",
        "COMM": "comment",
        "TENC": "producer",
        "TRCK": "track_number",
        "TALB": "album",
        "TIT2": "title",
        "TYER": "creation_date",
        "WXXX": "url",
        "TCON": "music_genre",
        "TLAN": "language",
        "TCOP": "copyright",
        "TDAT": "creation_date",
        "TRDA": "creation_date",
        "TORY": "creation_date",
        "TIT1": "title",
    }

    def processID3v2(self, field):
        # Read value
        if "content" not in field:
            return
        content = field["content"]
        if "text" not in content:
            return
        if "title" in content and content["title"].value:
            value = "%s: %s" % (content["title"].value, content["text"].value)
        else:
            value = content["text"].value

        # Known tag?
        tag = field["tag"].value
        if tag not in self.TAG_TO_KEY:
            if tag:
                if isinstance(tag, str):
                    tag = makePrintable(tag, "ISO-8859-1", to_unicode=True)
                self.warning("Skip ID3v2 tag %s: %s" % (tag, value))
            return
        key = self.TAG_TO_KEY[tag]
        setattr(self, key, value)

    def readID3v2(self, id3):
        for field in id3:
            if field.is_field_set and "tag" in field:
                self.processID3v2(field)

    def extract(self, mp3):
        if "/frames/frame[0]" in mp3:
            frame = mp3["/frames/frame[0]"]
            self.nb_channel = (frame.getNbChannel(), frame["channel_mode"].display)
            self.format_version = u"MPEG version %s layer %s" % \
                (frame["version"].display, frame["layer"].display)
            self.sample_rate = frame.getSampleRate()
            self.bits_per_sample = 16
            if mp3["frames"].looksConstantBitRate():
                self.computeBitrate(frame)
            else:
                self.computeVariableBitrate(mp3)
        if "id3v1" in mp3:
            id3 = mp3["id3v1"]
            self.comment = id3["comment"].value
            self.author = id3["author"].value
            self.title = id3["song"].value
            self.album = id3["album"].value
            if id3["year"].value != "0":
                self.creation_date = id3["year"].value
            if "track_nb" in id3:
                self.track_number = id3["track_nb"].value
        if "id3v2" in mp3:
            self.readID3v2(mp3["id3v2"])
        if "frames" in mp3:
            computeComprRate(self, mp3["frames"].size)

    def computeBitrate(self, frame):
        bit_rate = frame.getBitRate() # may returns None on error
        if not bit_rate:
            return
        self.bit_rate = (bit_rate, _("%s (constant)") % humanBitRate(bit_rate))
        self.duration = timedelta(seconds=float(frame["/frames"].size) / bit_rate)

    def computeVariableBitrate(self, mp3):
        if self.quality <= QUALITY_FAST:
            return
        count = 0
        if QUALITY_BEST <= self.quality:
            self.warning("Process all MPEG audio frames to compute exact duration")
            max_count = None
        else:
            max_count = 500 * self.quality
        total_bit_rate = 0.0
        for index, frame in enumerate(mp3.array("frames/frame")):
            if index < 3:
                continue
            bit_rate = frame.getBitRate()
            if bit_rate:
                total_bit_rate += float(bit_rate)
                count += 1
                if max_count and max_count <= count:
                    break
        if not count:
            return
        bit_rate = total_bit_rate / count
        self.bit_rate = (bit_rate,
            _("%s (Variable bit rate)") % humanBitRate(bit_rate))
        duration = timedelta(seconds=float(mp3["frames"].size) / bit_rate)
        self.duration = duration

class AiffMetadata(RootMetadata):
    def extract(self, aiff):
        if "common" in aiff:
            self.useCommon(aiff["common"])
        computeBitRate(self)

    @fault_tolerant
    def useCommon(self, info):
        self.nb_channel = info["nb_channel"].value
        self.bits_per_sample = info["sample_size"].value
        self.sample_rate = getValue(info, "sample_rate")
        if self.has("sample_rate"):
            rate = self.get("sample_rate")
            if rate:
                sec = float(info["nb_sample"].value) / rate
                self.duration = timedelta(seconds=sec)
        if "codec" in info:
            self.compression = info["codec"].display

class FlacMetadata(RootMetadata):
    def extract(self, flac):
        if "metadata/stream_info/content" in flac:
            self.useStreamInfo(flac["metadata/stream_info/content"])
        if "metadata/comment/content" in flac:
            readVorbisComment(self, flac["metadata/comment/content"])

    @fault_tolerant
    def useStreamInfo(self, info):
        self.nb_channel = info["nb_channel"].value + 1
        self.bits_per_sample = info["bits_per_sample"].value + 1
        self.sample_rate = info["sample_hertz"].value
        sec = info["total_samples"].value
        if sec:
            sec = float(sec) / info["sample_hertz"].value
            self.duration = timedelta(seconds=sec)

registerExtractor(AuFile, AuMetadata)
registerExtractor(MpegAudioFile, MpegAudioMetadata)
registerExtractor(OggFile, OggMetadata)
registerExtractor(RealMediaFile, RealMediaMetadata)
registerExtractor(RealAudioFile, RealAudioMetadata)
registerExtractor(AiffFile, AiffMetadata)
registerExtractor(FlacParser, FlacMetadata)

