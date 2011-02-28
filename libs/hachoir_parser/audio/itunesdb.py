"""
iPod iTunesDB parser.

Documentation:
- http://ipodlinux.org/ITunesDB

Author: Romain HERAULT
Creation date: 19 august 2006
"""

from hachoir_parser import Parser
from hachoir_core.field import (FieldSet,
    UInt8, UInt16, UInt32, UInt64, TimestampMac32,
    String, Float32, NullBytes, Enum)
from hachoir_core.endian import LITTLE_ENDIAN
from hachoir_core.tools import humanDuration
from hachoir_core.text_handler import displayHandler, filesizeHandler

list_order={
        1 : "playlist order (manual sort order)",
        2 : "???",
        3 : "songtitle",
        4 : "album",
        5 : "artist",
        6 : "bitrate",
        7 : "genre",
        8 : "kind",
        9 : "date modified",
        10 : "track number",
        11 : "size",
        12 : "time",
        13 : "year",
        14 : "sample rate",
        15 : "comment",
        16 : "date added",
        17 : "equalizer",
        18 : "composer",
        19 : "???",
        20 : "play count",
        21 : "last played",
        22 : "disc number",
        23 : "my rating",
        24 : "release date",
        25 : "BPM",
        26 : "grouping",
        27 : "category",
        28 : "description",
        29 : "show",
        30 : "season",
        31 : "episode number"
    }

class DataObject(FieldSet):
    type_name={
        1:"Title",
        2:"Location",
        3:"Album",
        4:"Artist",
        5:"Genre",
        6:"Filetype",
        7:"EQ Setting",
        8:"Comment",
        9:"Category",
        12:"Composer",
        13:"Grouping",
        14:"Description text",
        15:"Podcast Enclosure URL",
        16:"Podcast RSS URL",
        17:"Chapter data",
        18:"Subtitle",
        19:"Show (for TV Shows only)",
        20:"Episode",
        21:"TV Network",
        50:"Smart Playlist Data",
        51:"Smart Playlist Rules",
        52:"Library Playlist Index",
        100:"Column info",
    }

    mhod52_sort_index_type_name={
        3:"Title",
        4:"Album, then Disk/Tracknumber, then Title",
        5:"Artist, then Album, then Disc/Tracknumber, then Title",
        7:"Genre, then Artist, then Album, then Disc/Tracknumber, then Title",
        8:"Composer, then Title"
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["entry_length"].value *8

    def createFields(self):
        yield String(self, "header_id", 4, "Data Object Header Markup (\"mhod\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "entry_length", "Entry Length")
        yield Enum(UInt32(self, "type", "type"),self.type_name)
        if(self["type"].value<15):
            yield UInt32(self, "unknown[]")
            yield UInt32(self, "unknown[]")
            yield UInt32(self, "position", "Position")
            yield UInt32(self, "length", "String Length in bytes")
            yield UInt32(self, "unknown[]")
            yield UInt32(self, "unknown[]")
            yield String(self, "string", self["length"].value, "String Data", charset="UTF-16-LE")
        elif (self["type"].value<17):
            yield UInt32(self, "unknown[]")
            yield UInt32(self, "unknown[]")
            yield String(self, "string", self._size/8-self["header_length"].value, "String Data", charset="UTF-8")
        elif (self["type"].value == 52):
            yield UInt32(self, "unknown[]", "unk1")
            yield UInt32(self, "unknown[]", "unk2")
            yield Enum(UInt32(self, "sort_index_type", "Sort Index Type"),self.mhod52_sort_index_type_name)
            yield UInt32(self, "entry_count", "Entry Count")
            indexes_size = self["entry_count"].value*4
            padding_offset = self["entry_length"].value - indexes_size
            padding = self.seekByte(padding_offset, "header padding")
            if padding:
                yield padding
            for i in xrange(self["entry_count"].value):
                yield UInt32(self, "index["+str(i)+"]", "Index of the "+str(i)+"nth mhit")
        else:
            padding = self.seekByte(self["header_length"].value, "header padding")
            if padding:
                yield padding
        padding = self.seekBit(self._size, "entry padding")
        if padding:
            yield padding

class TrackItem(FieldSet):
    x1_type_name={
        0:"AAC or CBR MP3",
        1:"VBR MP3"
    }
    x2_type_name={
        0:"AAC",
        1:"MP3"
    }
    media_type_name={
        0x00:"Audio/Video",
        0x01:"Audio",
        0x02:"Video",
        0x04:"Podcast",
        0x06:"Video Podcast",
        0x08:"Audiobook",
        0x20:"Music Video",
        0x40:"TV Show",
        0X60:"TV Show (Music lists)",
    }
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["entry_length"].value *8

    def createFields(self):
        yield String(self, "header_id", 4, "Track Item Header Markup (\"mhit\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "entry_length", "Entry Length")
        yield UInt32(self, "string_number", "Number of Strings")
        yield UInt32(self, "unique_id", "Unique ID")
        yield UInt32(self, "visible_tag", "Visible Tag")
        yield String(self, "file_type", 4, "File Type")
        yield Enum(UInt8(self, "x1_type", "Extended Type 1"),self.x1_type_name)
        yield Enum(UInt8(self, "x2_type", "Extended type 2"),self.x2_type_name)
        yield UInt8(self, "compilation_flag", "Compilation Flag")
        yield UInt8(self, "rating", "Rating")
        yield TimestampMac32(self, "added_date", "Date when the item was added")
        yield filesizeHandler(UInt32(self, "size", "Track size in bytes"))
        yield displayHandler(UInt32(self, "length", "Track length in milliseconds"), humanDuration)
        yield UInt32(self, "track_number", "Number of this track")
        yield UInt32(self, "total_track", "Total number of tracks")
        yield UInt32(self, "year", "Year of the track")
        yield UInt32(self, "bitrate", "Bitrate")
        yield UInt32(self, "samplerate", "Sample Rate")
        yield UInt32(self, "volume", "volume")
        yield UInt32(self, "start_time", "Start playing at, in milliseconds")
        yield UInt32(self, "stop_time", "Stop playing at,  in milliseconds")
        yield UInt32(self, "soundcheck", "SoundCheck preamp")
        yield UInt32(self, "playcount_1", "Play count of the track")
        yield UInt32(self, "playcount_2", "Play count of the track (identical to playcount_1)")
        yield UInt32(self, "last_played_time", "Time the song was last played")
        yield UInt32(self, "disc_number", "disc number in multi disc sets")
        yield UInt32(self, "total_discs", "Total number of discs in the disc set")
        yield UInt32(self, "userid", "User ID in the DRM scheme")
        yield TimestampMac32(self, "last_modified", "Time of the last modification of the track")
        yield UInt32(self, "bookmark_time", "Bookmark time for AudioBook")
        yield UInt64(self, "dbid", "Unique DataBase ID for the song (identical in mhit and in mhii)")
        yield UInt8(self, "checked", "song is checked")
        yield UInt8(self, "application_rating", "Last Rating before change")
        yield UInt16(self, "BPM", "BPM of the track")
        yield UInt16(self, "artwork_count", "number of artworks fo this item")
        yield UInt16(self, "unknown[]")
        yield UInt32(self, "artwork_size", "Total size of artworks in bytes")
        yield UInt32(self, "unknown[]")
        yield Float32(self, "sample_rate_2", "Sample Rate express in float")
        yield UInt32(self, "released_date", "Date of release in Music Store or in Podcast")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt8(self, "has_artwork", "0x01 for track with artwork, 0x02 otherwise")
        yield UInt8(self, "skip_wen_shuffling", "Skip that track when shuffling")
        yield UInt8(self, "remember_playback_position", "Remember playback position")
        yield UInt8(self, "flag4", "Flag 4")
        yield UInt64(self, "dbid2", "Unique DataBase ID for the song (identical as above)")
        yield UInt8(self, "lyrics_flag", "Lyrics Flag")
        yield UInt8(self, "movie_file_flag", "Movie File Flag")
        yield UInt8(self, "played_mark", "Track has been played")
        yield UInt8(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "sample_count", "Number of samples in the song (only for WAV and AAC files)")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield Enum(UInt32(self, "media_type", "Media Type for video iPod"),self.media_type_name)
        yield UInt32(self, "season_number", "Season Number")
        yield UInt32(self, "episode_number", "Episode Number")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "unknown[]")
        padding = self.seekByte(self["header_length"].value, "header padding")
        if padding:
            yield padding

        #while ((self.stream.readBytes(0, 4) == 'mhod') and  ((self.current_size/8) < self["entry_length"].value)):
        for i in xrange(self["string_number"].value):
            yield DataObject(self, "data[]")
        padding = self.seekBit(self._size, "entry padding")
        if padding:
            yield padding

class TrackList(FieldSet):
    def createFields(self):
        yield String(self, "header_id", 4, "Track List Header Markup (\"mhlt\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "track_number", "Number of Tracks")

        padding = self.seekByte(self["header_length"].value, "header padding")
        if padding:
            yield padding

        for i in xrange(self["track_number"].value):
            yield TrackItem(self, "track[]")

class PlaylistItem(FieldSet):
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["entry_length"].value *8

    def createFields(self):
        yield String(self, "header_id", 4, "Playlist Item Header Markup (\"mhip\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "entry_length", "Entry Length")
        yield UInt32(self, "data_object_child_count", "Number of Child Data Objects")
        yield UInt32(self, "podcast_grouping_flag", "Podcast Grouping Flag")
        yield UInt32(self, "group_id", "Group ID")
        yield UInt32(self, "track_id", "Track ID")
        yield TimestampMac32(self, "timestamp", "Song Timestamp")
        yield UInt32(self, "podcast_grouping_ref", "Podcast Grouping Reference")
        padding = self.seekByte(self["header_length"].value, "header padding")
        if padding:
            yield padding

        for i in xrange(self["data_object_child_count"].value):
            yield DataObject(self, "mhod[]")


class Playlist(FieldSet):
    is_master_pl_name={
        0:"Regular playlist",
        1:"Master playlist"
    }

    is_podcast_name={
        0:"Normal Playlist List",
        1:"Podcast Playlist List"
    }

    list_sort_order_name={
        1:"Manual Sort Order",
        2:"???",
        3:"Song Title",
        4:"Album",
        5:"Artist",
        6:"Bitrate",
        7:"Genre",
        8:"Kind",
        9:"Date Modified",
        10:"Track Number",
        11:"Size",
        12:"Time",
        13:"Year",
        14:"Sample Rate",
        15:"Comment",
        16:"Date Added",
        17:"Equalizer",
        18:"Composer",
        19:"???",
        20:"Play Count",
        21:"Last Played",
        22:"Disc Number",
        23:"My Rating",
        24:"Release Date",
        25:"BPM",
        26:"Grouping",
        27:"Category",
        28:"Description",
        29:"Show",
        30:"Season",
        31:"Episode Number"
    }

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["entry_length"].value *8

    def createFields(self):
        yield String(self, "header_id", 4, "Playlist List Header Markup (\"mhyp\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "entry_length", "Entry Length")
        yield UInt32(self, "data_object_child_count", "Number of Child Data Objects")
        yield UInt32(self, "playlist_count", "Number of Playlist Items")
        yield Enum(UInt8(self, "type", "Normal or master playlist?"), self.is_master_pl_name)
        yield UInt8(self, "XXX1", "XXX1")
        yield UInt8(self, "XXX2", "XXX2")
        yield UInt8(self, "XXX3", "XXX3")
        yield TimestampMac32(self, "creation_date", "Date when the playlist was created")
        yield UInt64(self, "playlistid", "Persistent Playlist ID")
        yield UInt32(self, "unk3", "unk3")
        yield UInt16(self, "string_mhod_count", "Number of string MHODs for this playlist")
        yield Enum(UInt16(self, "is_podcast", "Playlist or Podcast List?"), self.is_podcast_name)
        yield Enum(UInt32(self, "sort_order", "Playlist Sort Order"), self.list_sort_order_name)

        padding = self.seekByte(self["header_length"].value, "entry padding")
        if padding:
            yield padding

        for i in xrange(self["data_object_child_count"].value):
            yield DataObject(self, "mhod[]")

        for i in xrange(self["playlist_count"].value):
            yield PlaylistItem(self, "playlist_item[]")



class PlaylistList(FieldSet):
    def createFields(self):
        yield String(self, "header_id", 4, "Playlist List Header Markup (\"mhlp\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "playlist_number", "Number of Playlists")

        padding = self.seekByte(self["header_length"].value, "header padding")
        if padding:
            yield padding

        for i in xrange(self["playlist_number"].value):
            yield Playlist(self, "playlist[]")

class DataSet(FieldSet):
    type_name={
        1:"Track List",
        2:"Play List",
        3:"Podcast List"
        }
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["entry_length"].value *8

    def createFields(self):
        yield String(self, "header_id", 4, "DataSet Header Markup (\"mhsd\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "entry_length", "Entry Length")
        yield Enum(UInt32(self, "type", "type"),self.type_name)
        padding = self.seekByte(self["header_length"].value, "header_raw")
        if padding:
            yield padding
        if self["type"].value == 1:
            yield TrackList(self, "tracklist[]")
        if self["type"].value == 2:
            yield PlaylistList(self, "playlist_list[]");
        if self["type"].value == 3:
            yield PlaylistList(self, "podcast_list[]");
        padding = self.seekBit(self._size, "entry padding")
        if padding:
            yield padding

class DataBase(FieldSet):
    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._size = self["entry_length"].value *8

#    def createFields(self):

class ITunesDBFile(Parser):
    PARSER_TAGS = {
        "id": "itunesdb",
        "category": "audio",
        "min_size": 44*8,
        "magic": (('mhbd',0),),
        "description": "iPod iTunesDB file"
    }

    endian = LITTLE_ENDIAN

    def validate(self):
        return self.stream.readBytes(0, 4) == 'mhbd'

    def createFields(self):
        yield String(self, "header_id", 4, "DataBase Header Markup (\"mhbd\")", charset="ISO-8859-1")
        yield UInt32(self, "header_length", "Header Length")
        yield UInt32(self, "entry_length", "Entry Length")
        yield UInt32(self, "unknown[]")
        yield UInt32(self, "version_number", "Version Number")
        yield UInt32(self, "child_number", "Number of Children")
        yield UInt64(self, "id", "ID for this database")
        yield UInt32(self, "unknown[]")
        yield UInt64(self, "initial_dbid", "Initial DBID")
        size = self["header_length"].value-self.current_size/ 8
        if size>0:
            yield NullBytes(self, "padding", size)
        for i in xrange(self["child_number"].value):
            yield DataSet(self, "dataset[]")
        padding = self.seekByte(self["entry_length"].value, "entry padding")
        if padding:
            yield padding

    def createContentSize(self):
        return self["entry_length"].value * 8

