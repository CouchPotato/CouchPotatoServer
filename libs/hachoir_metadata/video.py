from hachoir_core.field import MissingField
from hachoir_metadata.metadata import (registerExtractor,
    Metadata, RootMetadata, MultipleMetadata)
from hachoir_metadata.metadata_item import QUALITY_GOOD
from hachoir_metadata.safe import fault_tolerant
from hachoir_parser.video import MovFile, AsfFile, FlvFile
from hachoir_parser.video.asf import Descriptor as ASF_Descriptor
from hachoir_parser.container import MkvFile
from hachoir_parser.container.mkv import dateToDatetime
from hachoir_core.i18n import _
from hachoir_core.tools import makeUnicode, makePrintable, timedelta2seconds
from datetime import timedelta

class MkvMetadata(MultipleMetadata):
    tag_key = {
        "TITLE": "title",
        "URL": "url",
        "COPYRIGHT": "copyright",

        # TODO: use maybe another name?
        # Its value may be different than (...)/Info/DateUTC/date
        "DATE_RECORDED": "creation_date",

        # TODO: Extract subtitle metadata
        "SUBTITLE": "subtitle_author",
    }

    def extract(self, mkv):
        for segment in mkv.array("Segment"):
            self.processSegment(segment)

    def processSegment(self, segment):
        for field in segment:
            if field.name.startswith("Info["):
                self.processInfo(field)
            elif field.name.startswith("Tags["):
                for tag in field.array("Tag"):
                    self.processTag(tag)
            elif field.name.startswith("Tracks["):
                self.processTracks(field)
            elif field.name.startswith("Cluster["):
                if self.quality < QUALITY_GOOD:
                    return

    def processTracks(self, tracks):
        for entry in tracks.array("TrackEntry"):
            self.processTrack(entry)

    def processTrack(self, track):
        if "TrackType/enum" not in track:
            return
        if track["TrackType/enum"].display == "video":
            self.processVideo(track)
        elif track["TrackType/enum"].display == "audio":
            self.processAudio(track)
        elif track["TrackType/enum"].display == "subtitle":
            self.processSubtitle(track)

    def trackCommon(self, track, meta):
        if "Name/unicode" in track:
            meta.title = track["Name/unicode"].value
        if "Language/string" in track \
        and track["Language/string"].value not in ("mis", "und"):
            meta.language = track["Language/string"].value

    def processVideo(self, track):
        video = Metadata(self)
        self.trackCommon(track, video)
        try:
            video.compression = track["CodecID/string"].value
            if "Video" in track:
                video.width = track["Video/PixelWidth/unsigned"].value
                video.height = track["Video/PixelHeight/unsigned"].value
        except MissingField:
            pass
        self.addGroup("video[]", video, "Video stream")

    def getDouble(self, field, parent):
        float_key = '%s/float' % parent
        if float_key in field:
            return field[float_key].value
        double_key = '%s/double' % parent
        if double_key in field:
            return field[double_key].value
        return None

    def processAudio(self, track):
        audio = Metadata(self)
        self.trackCommon(track, audio)
        if "Audio" in track:
            frequency = self.getDouble(track, "Audio/SamplingFrequency")
            if frequency is not None:
                audio.sample_rate = frequency
            if "Audio/Channels/unsigned" in track:
                audio.nb_channel = track["Audio/Channels/unsigned"].value
            if "Audio/BitDepth/unsigned" in track:
                audio.bits_per_sample = track["Audio/BitDepth/unsigned"].value
        if "CodecID/string" in track:
            audio.compression = track["CodecID/string"].value
        self.addGroup("audio[]", audio, "Audio stream")

    def processSubtitle(self, track):
        sub = Metadata(self)
        self.trackCommon(track, sub)
        try:
            sub.compression = track["CodecID/string"].value
        except MissingField:
            pass
        self.addGroup("subtitle[]", sub, "Subtitle")

    def processTag(self, tag):
        for field in tag.array("SimpleTag"):
            self.processSimpleTag(field)

    def processSimpleTag(self, tag):
        if "TagName/unicode" not in tag \
        or "TagString/unicode" not in tag:
            return
        name = tag["TagName/unicode"].value
        if name not in self.tag_key:
            return
        key = self.tag_key[name]
        value = tag["TagString/unicode"].value
        setattr(self, key, value)

    def processInfo(self, info):
        if "TimecodeScale/unsigned" in info:
            duration = self.getDouble(info, "Duration")
            if duration is not None:
                try:
                    seconds = duration * info["TimecodeScale/unsigned"].value * 1e-9
                    self.duration = timedelta(seconds=seconds)
                except OverflowError:
                    # Catch OverflowError for timedelta (long int too large
                    # to be converted to an int)
                    pass
        if "DateUTC/date" in info:
            try:
                self.creation_date = dateToDatetime(info["DateUTC/date"].value)
            except OverflowError:
                pass
        if "WritingApp/unicode" in info:
            self.producer = info["WritingApp/unicode"].value
        if "MuxingApp/unicode" in info:
            self.producer = info["MuxingApp/unicode"].value
        if "Title/unicode" in info:
            self.title = info["Title/unicode"].value

class FlvMetadata(MultipleMetadata):
    def extract(self, flv):
        if "video[0]" in flv:
            meta = Metadata(self)
            self.extractVideo(flv["video[0]"], meta)
            self.addGroup("video", meta, "Video stream")
        if "audio[0]" in flv:
            meta = Metadata(self)
            self.extractAudio(flv["audio[0]"], meta)
            self.addGroup("audio", meta, "Audio stream")
        # TODO: Computer duration
        # One technic: use last video/audio chunk and use timestamp
        # But this is very slow
        self.format_version = flv.description

        if "metadata/entry[1]" in flv:
            self.extractAMF(flv["metadata/entry[1]"])
        if self.has('duration'):
            self.bit_rate = flv.size / timedelta2seconds(self.get('duration'))

    @fault_tolerant
    def extractAudio(self, audio, meta):
        if audio["codec"].display == "MP3" and "music_data" in audio:
            meta.compression = audio["music_data"].description
        else:
            meta.compression = audio["codec"].display
        meta.sample_rate = audio.getSampleRate()
        if audio["is_16bit"].value:
            meta.bits_per_sample = 16
        else:
            meta.bits_per_sample = 8
        if audio["is_stereo"].value:
            meta.nb_channel = 2
        else:
            meta.nb_channel = 1

    @fault_tolerant
    def extractVideo(self, video, meta):
        meta.compression = video["codec"].display

    def extractAMF(self, amf):
        for entry in amf.array("item"):
            self.useAmfEntry(entry)

    @fault_tolerant
    def useAmfEntry(self, entry):
        key = entry["key"].value
        if key == "duration":
            self.duration = timedelta(seconds=entry["value"].value)
        elif key == "creator":
            self.producer = entry["value"].value
        elif key == "audiosamplerate":
            self.sample_rate = entry["value"].value
        elif key == "framerate":
            self.frame_rate = entry["value"].value
        elif key == "metadatacreator":
            self.producer = entry["value"].value
        elif key == "metadatadate":
            self.creation_date = entry.value
        elif key == "width":
            self.width = int(entry["value"].value)
        elif key == "height":
            self.height = int(entry["value"].value)

class MovMetadata(RootMetadata):
    def extract(self, mov):
        for atom in mov:
            if "movie" in atom:
                self.processMovie(atom["movie"])

    @fault_tolerant
    def processMovieHeader(self, hdr):
        self.creation_date = hdr["creation_date"].value
        self.last_modification = hdr["lastmod_date"].value
        self.duration = timedelta(seconds=float(hdr["duration"].value) / hdr["time_scale"].value)
        self.comment = _("Play speed: %.1f%%") % (hdr["play_speed"].value*100)
        self.comment = _("User volume: %.1f%%") % (float(hdr["volume"].value)*100//255)

    @fault_tolerant
    def processTrackHeader(self, hdr):
        width = int(hdr["frame_size_width"].value)
        height = int(hdr["frame_size_height"].value)
        if width and height:
            self.width = width
            self.height = height

    def processTrack(self, atom):
        for field in atom:
            if "track_hdr" in field:
                self.processTrackHeader(field["track_hdr"])

    def processMovie(self, atom):
        for field in atom:
            if "track" in field:
                self.processTrack(field["track"])
            if "movie_hdr" in field:
                self.processMovieHeader(field["movie_hdr"])


class AsfMetadata(MultipleMetadata):
    EXT_DESC_TO_ATTR = {
        "Encoder": "producer",
        "ToolName": "producer",
        "AlbumTitle": "album",
        "Track": "track_number",
        "TrackNumber": "track_total",
        "Year": "creation_date",
        "AlbumArtist": "author",
    }
    SKIP_EXT_DESC = set((
        # Useless informations
        "WMFSDKNeeded", "WMFSDKVersion",
        "Buffer Average", "VBR Peak", "EncodingTime",
        "MediaPrimaryClassID", "UniqueFileIdentifier",
    ))

    def extract(self, asf):
        if "header/content" in asf:
            self.processHeader(asf["header/content"])

    def processHeader(self, header):
        compression = []
        is_vbr = None

        if "ext_desc/content" in header:
            # Extract all data from ext_desc
            data = {}
            for desc in header.array("ext_desc/content/descriptor"):
                self.useExtDescItem(desc, data)

            # Have ToolName and ToolVersion? If yes, group them to producer key
            if "ToolName" in data and "ToolVersion" in data:
                self.producer = "%s (version %s)" % (data["ToolName"], data["ToolVersion"])
                del data["ToolName"]
                del data["ToolVersion"]

            # "IsVBR" key
            if "IsVBR" in data:
                is_vbr = (data["IsVBR"] == 1)
                del data["IsVBR"]

            # Store data
            for key, value in data.iteritems():
                if key in self.EXT_DESC_TO_ATTR:
                    key = self.EXT_DESC_TO_ATTR[key]
                else:
                    if isinstance(key, str):
                        key = makePrintable(key, "ISO-8859-1", to_unicode=True)
                    value = "%s=%s" % (key, value)
                    key = "comment"
                setattr(self, key, value)

        if "file_prop/content" in header:
            self.useFileProp(header["file_prop/content"], is_vbr)

        if "codec_list/content" in header:
            for codec in header.array("codec_list/content/codec"):
                if "name" in codec:
                    text = codec["name"].value
                    if "desc" in codec and codec["desc"].value:
                        text = "%s (%s)" % (text, codec["desc"].value)
                    compression.append(text)

        audio_index = 1
        video_index = 1
        for index, stream_prop in enumerate(header.array("stream_prop")):
            if "content/audio_header" in stream_prop:
                meta = Metadata(self)
                self.streamProperty(header, index, meta)
                self.streamAudioHeader(stream_prop["content/audio_header"], meta)
                if self.addGroup("audio[%u]" % audio_index, meta, "Audio stream #%u" % audio_index):
                    audio_index += 1
            elif "content/video_header" in stream_prop:
                meta = Metadata(self)
                self.streamProperty(header, index, meta)
                self.streamVideoHeader(stream_prop["content/video_header"], meta)
                if self.addGroup("video[%u]" % video_index, meta, "Video stream #%u" % video_index):
                    video_index += 1

        if "metadata/content" in header:
            info = header["metadata/content"]
            try:
                self.title = info["title"].value
                self.author = info["author"].value
                self.copyright = info["copyright"].value
            except MissingField:
                pass

    @fault_tolerant
    def streamAudioHeader(self, audio, meta):
        if not meta.has("compression"):
            meta.compression = audio["twocc"].display
        meta.nb_channel = audio["channels"].value
        meta.sample_rate = audio["sample_rate"].value
        meta.bits_per_sample = audio["bits_per_sample"].value

    @fault_tolerant
    def streamVideoHeader(self, video, meta):
        meta.width = video["width"].value
        meta.height = video["height"].value
        if "bmp_info" in video:
            bmp_info = video["bmp_info"]
            if not meta.has("compression"):
                meta.compression = bmp_info["codec"].display
            meta.bits_per_pixel = bmp_info["bpp"].value

    @fault_tolerant
    def useExtDescItem(self, desc, data):
        if desc["type"].value == ASF_Descriptor.TYPE_BYTE_ARRAY:
            # Skip binary data
            return
        key = desc["name"].value
        if "/" in key:
            # Replace "WM/ToolName" with "ToolName"
            key = key.split("/", 1)[1]
        if key in self.SKIP_EXT_DESC:
            # Skip some keys
            return
        value = desc["value"].value
        if not value:
            return
        value = makeUnicode(value)
        data[key] = value

    @fault_tolerant
    def useFileProp(self, prop, is_vbr):
        self.creation_date = prop["creation_date"].value
        self.duration = prop["play_duration"].value
        if prop["seekable"].value:
            self.comment = u"Is seekable"
        value = prop["max_bitrate"].value
        text = prop["max_bitrate"].display
        if is_vbr is True:
            text = "VBR (%s max)" % text
        elif is_vbr is False:
            text = "%s (CBR)" % text
        else:
            text = "%s (max)" % text
        self.bit_rate = (value, text)

    def streamProperty(self, header, index, meta):
        key = "bit_rates/content/bit_rate[%u]/avg_bitrate" % index
        if key in header:
            meta.bit_rate = header[key].value

        # TODO: Use codec list
        # It doesn't work when the video uses /header/content/bitrate_mutex
        # since the codec list are shared between streams but... how is it
        # shared?
#        key = "codec_list/content/codec[%u]" % index
#        if key in header:
#            codec = header[key]
#            if "name" in codec:
#                text = codec["name"].value
#                if "desc" in codec and codec["desc"].value:
#                    meta.compression = "%s (%s)" % (text, codec["desc"].value)
#                else:
#                    meta.compression = text

registerExtractor(MovFile, MovMetadata)
registerExtractor(AsfFile, AsfMetadata)
registerExtractor(FlvFile, FlvMetadata)
registerExtractor(MkvFile, MkvMetadata)

