from hachoir_parser import createParser
from hachoir_metadata import extractMetadata
from hachoir_core.cmd_line import unicodeFilename

import datetime
import json
import sys
import re


def getMetadata(filename):
    filename, realname = unicodeFilename(filename), filename
    parser = createParser(filename, realname)
    try:
        metadata = extractMetadata(parser)
    except:
        return None

    if metadata is not None:
        metadata = metadata.exportPlaintext()
        return metadata
    return None

def parseMetadata(meta, jsonsafe=True):
    '''
    Return a dict of section headings like 'Video stream' or 'Audio stream'.  Each key will have a list of dicts.
    This supports multiple video/audio/subtitle/whatever streams per stream type.  Each element in the list of streams
    will he a dict with keys like 'Image height' and 'Compression'...anything that hachoir is able to extract.

    An example output:
    {'Audio stream': [{u'Channel': u'6',
                       u'Compression': u'A_AC3',
                       u'Sample rate': u'48.0 kHz'}],
     u'Common': [{u'Creation date': u'2008-03-20 09:09:43',
                  u'Duration': u'1 hour 40 min 6 sec',
                  u'Endianness': u'Big endian',
                  u'MIME type': u'video/x-matroska',
                  u'Producer': u'libebml v0.7.7 + libmatroska v0.8.1'}],
     'Video stream': [{u'Compression': u'V_MPEG4/ISO/AVC',
                       u'Image height': u'688 pixels',
                       u'Image width': u'1280 pixels',
                       u'Language': u'English'}]}
    '''
    if not meta:
        return
    sections = {}
    what = []
    for line in meta:
        #if line doesn't start with "- " it is a section heading
        if line[:2] != "- ":
            section = line.strip(":").lower()

            #lets collapse multiple stream headings into one...
            search = re.search(r'#\d+\Z', section)
            if search:
                section = re.sub(search.group(), '', section).strip()

            if section not in sections:
                sections[section] = [dict()]
            else:
                sections[section].append(dict())
        else:
            #This isn't a section heading, so we put it in the last section heading we found.
            #meta always starts out with a section heading so 'section' will always be defined
            i = line.find(":")
            key = line[2:i].lower()
            value = _parseValue(section, key, line[i+2:])

            if value is None:
                value = line[i+2:]

            if jsonsafe:
                try:
                    v = json.dumps(value)
                except TypeError:
                    value = str(value)

            sections[section][-1][key] = value



    return sections

def _parseValue(section, key, value, jsonsafe = True):
    '''
    Tediously check all the types that we know about (checked over 7k videos to find these)
    and convert them to python native types.

    If jsonsafe is True, we'll make json-unfriendly types like datetime into json-friendly.
    '''

    date_search = re.search("\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d", value)

    if key == 'bit rate':
        ret = _parseBitRate(value.lower())
    elif key == 'bits/sample' or key == 'bits/pixel':
        try:
            bits = int(value.split()[0])
            ret = bits
        except:
            ret = None
    elif key == 'channel':
        if value == 'stereo':
            ret = 2
        elif value == 'mono':
            ret = 1
        else:
            try:
                channels = int(value)
                ret = channels
            except:
                ret = None
    elif key == 'compression':
        ret = _parseCompression(value)
    elif key == 'compression rate':
        try:
            ret = float(value.split('x')[0])
        except:
            ret = None
    elif key == 'duration':
        try:
            ret = _parseDuration(value)
        except:
            ret = None
    elif key == 'sample rate':
        try:
            ret = float(value.split()[0]) * 1000
        except:
            ret = None
    elif key == 'frame rate':
        try:
            ret = float(value.split()[0])
        except:
            pass
    elif key == 'image height' or key == 'image width':
        pixels =  re.match("(?P<pixels>\d{1,4}) pixel", value)
        if pixels:
            ret = int(pixels.group('pixels'))
        else:
            ret = None
    elif date_search:
        try:
            ret = datetime.datetime.strptime(date_search.group(), "%Y-%m-%d %H:%M:%S")
        except:
            ret = None
    else:
        #If it's something we don't know about...
        ret = None

    return ret

def _parseDuration(value):
    t = re.search(r"((?P<hour>\d+) hour(s|))? ?((?P<min>\d+) min)? ?((?P<sec>\d+) sec)? ?((?P<ms>\d+) ms)?", value)
    if t:
        hour = 0 if not t.group('hour') else int(t.group('hour'))
        min = 0 if not t.group('min') else int(t.group('min'))
        sec = 0 if not t.group('sec') else int(t.group('sec'))
        ms = 0 if not t.group('ms') else int(t.group('ms'))
        return datetime.timedelta(hours = hour, minutes = min, seconds = sec, milliseconds = ms)

def _parseCompression(value):
    codecs = {
        'v_mpeg4/iso/avc': 'AVC',
        'x264': 'AVC',
        'divx': 'divx',
        'xvid': 'xvid',
        'v_ms/vfw/fourcc': 'vfw',
        'vorbis': 'vorbis',
        'xvid': 'xvid',
        'mpeg layer 3': 'mp3',
        'a_dts': 'DTS',
        'a_aac': 'AAC',
        'a_truehd': 'TRUEHD',
        'microsoft mpeg': 'MPEG',
        'ac3': 'AC3',
        'wvc1': 'WVC1',
        'pulse code modulation': 'PCM',
        'pcm': 'PCM',
        'windows media audio': 'WMA',
        'windows media video': 'WMV',
        's_text/ascii': 'ASCII',
        's_text/utf8': 'UTF8',
        's_text/ssa': 'SSA',
        's_text/ass': 'ASS'
    }
    for codec in codecs:
        if codec in value.lower():
            return codecs[codec]


def _parseBitRate(value):
    try:
        bitrate = float(value.split()[0])
    except:
        return None

    if 'kbit' in value.lower():
        multi = 1000
    elif 'mbit' in value.lower():
        multi = 1000 * 1000
    else:
        return None

    return bitrate * multi

print json.dumps(parseMetadata(getMetadata(sys.argv[1])))