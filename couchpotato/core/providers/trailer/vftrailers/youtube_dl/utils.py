#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import email.utils
import errno
import gzip
import io
import json
import locale
import os
import platform
import re
import socket
import sys
import traceback
import zlib

try:
    import urllib.request as compat_urllib_request
except ImportError: # Python 2
    import urllib2 as compat_urllib_request

try:
    import urllib.error as compat_urllib_error
except ImportError: # Python 2
    import urllib2 as compat_urllib_error

try:
    import urllib.parse as compat_urllib_parse
except ImportError: # Python 2
    import urllib as compat_urllib_parse

try:
    from urllib.parse import urlparse as compat_urllib_parse_urlparse
except ImportError: # Python 2
    from urlparse import urlparse as compat_urllib_parse_urlparse

try:
    import urllib.parse as compat_urlparse
except ImportError: # Python 2
    import urlparse as compat_urlparse

try:
    import http.cookiejar as compat_cookiejar
except ImportError: # Python 2
    import cookielib as compat_cookiejar

try:
    import html.entities as compat_html_entities
except ImportError: # Python 2
    import htmlentitydefs as compat_html_entities

try:
    import html.parser as compat_html_parser
except ImportError: # Python 2
    import HTMLParser as compat_html_parser

try:
    import http.client as compat_http_client
except ImportError: # Python 2
    import httplib as compat_http_client

try:
    from urllib.error import HTTPError as compat_HTTPError
except ImportError:  # Python 2
    from urllib2 import HTTPError as compat_HTTPError

try:
    from urllib.request import urlretrieve as compat_urlretrieve
except ImportError:  # Python 2
    from urllib import urlretrieve as compat_urlretrieve


try:
    from subprocess import DEVNULL
    compat_subprocess_get_DEVNULL = lambda: DEVNULL
except ImportError:
    compat_subprocess_get_DEVNULL = lambda: open(os.path.devnull, 'w')

try:
    from urllib.parse import parse_qs as compat_parse_qs
except ImportError: # Python 2
    # HACK: The following is the correct parse_qs implementation from cpython 3's stdlib.
    # Python 2's version is apparently totally broken
    def _unquote(string, encoding='utf-8', errors='replace'):
        if string == '':
            return string
        res = string.split('%')
        if len(res) == 1:
            return string
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'replace'
        # pct_sequence: contiguous sequence of percent-encoded bytes, decoded
        pct_sequence = b''
        string = res[0]
        for item in res[1:]:
            try:
                if not item:
                    raise ValueError
                pct_sequence += item[:2].decode('hex')
                rest = item[2:]
                if not rest:
                    # This segment was just a single percent-encoded character.
                    # May be part of a sequence of code units, so delay decoding.
                    # (Stored in pct_sequence).
                    continue
            except ValueError:
                rest = '%' + item
            # Encountered non-percent-encoded characters. Flush the current
            # pct_sequence.
            string += pct_sequence.decode(encoding, errors) + rest
            pct_sequence = b''
        if pct_sequence:
            # Flush the final pct_sequence
            string += pct_sequence.decode(encoding, errors)
        return string

    def _parse_qsl(qs, keep_blank_values=False, strict_parsing=False,
                encoding='utf-8', errors='replace'):
        qs, _coerce_result = qs, unicode
        pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
        r = []
        for name_value in pairs:
            if not name_value and not strict_parsing:
                continue
            nv = name_value.split('=', 1)
            if len(nv) != 2:
                if strict_parsing:
                    raise ValueError("bad query field: %r" % (name_value,))
                # Handle case of a control-name with no equal sign
                if keep_blank_values:
                    nv.append('')
                else:
                    continue
            if len(nv[1]) or keep_blank_values:
                name = nv[0].replace('+', ' ')
                name = _unquote(name, encoding=encoding, errors=errors)
                name = _coerce_result(name)
                value = nv[1].replace('+', ' ')
                value = _unquote(value, encoding=encoding, errors=errors)
                value = _coerce_result(value)
                r.append((name, value))
        return r

    def compat_parse_qs(qs, keep_blank_values=False, strict_parsing=False,
                encoding='utf-8', errors='replace'):
        parsed_result = {}
        pairs = _parse_qsl(qs, keep_blank_values, strict_parsing,
                        encoding=encoding, errors=errors)
        for name, value in pairs:
            if name in parsed_result:
                parsed_result[name].append(value)
            else:
                parsed_result[name] = [value]
        return parsed_result

try:
    compat_str = unicode # Python 2
except NameError:
    compat_str = str

try:
    compat_chr = unichr # Python 2
except NameError:
    compat_chr = chr

def compat_ord(c):
    if type(c) is int: return c
    else: return ord(c)

# This is not clearly defined otherwise
compiled_regex_type = type(re.compile(''))

std_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-us,en;q=0.5',
}

def preferredencoding():
    """Get preferred encoding.

    Returns the best encoding scheme for the system, based on
    locale.getpreferredencoding() and some further tweaks.
    """
    try:
        pref = locale.getpreferredencoding()
        u'TEST'.encode(pref)
    except:
        pref = 'UTF-8'

    return pref

if sys.version_info < (3,0):
    def compat_print(s):
        print(s.encode(preferredencoding(), 'xmlcharrefreplace'))
else:
    def compat_print(s):
        assert type(s) == type(u'')
        print(s)

# In Python 2.x, json.dump expects a bytestream.
# In Python 3.x, it writes to a character stream
if sys.version_info < (3,0):
    def write_json_file(obj, fn):
        with open(fn, 'wb') as f:
            json.dump(obj, f)
else:
    def write_json_file(obj, fn):
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(obj, f)

if sys.version_info >= (2,7):
    def find_xpath_attr(node, xpath, key, val):
        """ Find the xpath xpath[@key=val] """
        assert re.match(r'^[a-zA-Z]+$', key)
        assert re.match(r'^[a-zA-Z0-9@\s]*$', val)
        expr = xpath + u"[@%s='%s']" % (key, val)
        return node.find(expr)
else:
    def find_xpath_attr(node, xpath, key, val):
        for f in node.findall(xpath):
            if f.attrib.get(key) == val:
                return f
        return None

def htmlentity_transform(matchobj):
    """Transforms an HTML entity to a character.

    This function receives a match object and is intended to be used with
    the re.sub() function.
    """
    entity = matchobj.group(1)

    # Known non-numeric HTML entity
    if entity in compat_html_entities.name2codepoint:
        return compat_chr(compat_html_entities.name2codepoint[entity])

    mobj = re.match(u'(?u)#(x?\\d+)', entity)
    if mobj is not None:
        numstr = mobj.group(1)
        if numstr.startswith(u'x'):
            base = 16
            numstr = u'0%s' % numstr
        else:
            base = 10
        return compat_chr(int(numstr, base))

    # Unknown entity in name, return its literal representation
    return (u'&%s;' % entity)

compat_html_parser.locatestarttagend = re.compile(r"""<[a-zA-Z][-.a-zA-Z0-9:_]*(?:\s+(?:(?<=['"\s])[^\s/>][^\s/=>]*(?:\s*=+\s*(?:'[^']*'|"[^"]*"|(?!['"])[^>\s]*))?\s*)*)?\s*""", re.VERBOSE) # backport bugfix
class BaseHTMLParser(compat_html_parser.HTMLParser):
    def __init(self):
        compat_html_parser.HTMLParser.__init__(self)
        self.html = None

    def loads(self, html):
        self.html = html
        self.feed(html)
        self.close()

class AttrParser(BaseHTMLParser):
    """Modified HTMLParser that isolates a tag with the specified attribute"""
    def __init__(self, attribute, value):
        self.attribute = attribute
        self.value = value
        self.result = None
        self.started = False
        self.depth = {}
        self.watch_startpos = False
        self.error_count = 0
        BaseHTMLParser.__init__(self)

    def error(self, message):
        if self.error_count > 10 or self.started:
            raise compat_html_parser.HTMLParseError(message, self.getpos())
        self.rawdata = '\n'.join(self.html.split('\n')[self.getpos()[0]:]) # skip one line
        self.error_count += 1
        self.goahead(1)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.started:
            self.find_startpos(None)
        if self.attribute in attrs and attrs[self.attribute] == self.value:
            self.result = [tag]
            self.started = True
            self.watch_startpos = True
        if self.started:
            if not tag in self.depth: self.depth[tag] = 0
            self.depth[tag] += 1

    def handle_endtag(self, tag):
        if self.started:
            if tag in self.depth: self.depth[tag] -= 1
            if self.depth[self.result[0]] == 0:
                self.started = False
                self.result.append(self.getpos())

    def find_startpos(self, x):
        """Needed to put the start position of the result (self.result[1])
        after the opening tag with the requested id"""
        if self.watch_startpos:
            self.watch_startpos = False
            self.result.append(self.getpos())
    handle_entityref = handle_charref = handle_data = handle_comment = \
    handle_decl = handle_pi = unknown_decl = find_startpos

    def get_result(self):
        if self.result is None:
            return None
        if len(self.result) != 3:
            return None
        lines = self.html.split('\n')
        lines = lines[self.result[1][0]-1:self.result[2][0]]
        lines[0] = lines[0][self.result[1][1]:]
        if len(lines) == 1:
            lines[-1] = lines[-1][:self.result[2][1]-self.result[1][1]]
        lines[-1] = lines[-1][:self.result[2][1]]
        return '\n'.join(lines).strip()
# Hack for https://github.com/rg3/youtube-dl/issues/662
if sys.version_info < (2, 7, 3):
    AttrParser.parse_endtag = (lambda self, i:
        i + len("</scr'+'ipt>")
        if self.rawdata[i:].startswith("</scr'+'ipt>")
        else compat_html_parser.HTMLParser.parse_endtag(self, i))

def get_element_by_id(id, html):
    """Return the content of the tag with the specified ID in the passed HTML document"""
    return get_element_by_attribute("id", id, html)

def get_element_by_attribute(attribute, value, html):
    """Return the content of the tag with the specified attribute in the passed HTML document"""
    parser = AttrParser(attribute, value)
    try:
        parser.loads(html)
    except compat_html_parser.HTMLParseError:
        pass
    return parser.get_result()

class MetaParser(BaseHTMLParser):
    """
    Modified HTMLParser that isolates a meta tag with the specified name 
    attribute.
    """
    def __init__(self, name):
        BaseHTMLParser.__init__(self)
        self.name = name
        self.content = None
        self.result = None

    def handle_starttag(self, tag, attrs):
        if tag != 'meta':
            return
        attrs = dict(attrs)
        if attrs.get('name') == self.name:
            self.result = attrs.get('content')

    def get_result(self):
        return self.result

def get_meta_content(name, html):
    """
    Return the content attribute from the meta tag with the given name attribute.
    """
    parser = MetaParser(name)
    try:
        parser.loads(html)
    except compat_html_parser.HTMLParseError:
        pass
    return parser.get_result()


def clean_html(html):
    """Clean an HTML snippet into a readable string"""
    # Newline vs <br />
    html = html.replace('\n', ' ')
    html = re.sub(r'\s*<\s*br\s*/?\s*>\s*', '\n', html)
    html = re.sub(r'<\s*/\s*p\s*>\s*<\s*p[^>]*>', '\n', html)
    # Strip html tags
    html = re.sub('<.*?>', '', html)
    # Replace html entities
    html = unescapeHTML(html)
    return html.strip()


def sanitize_open(filename, open_mode):
    """Try to open the given filename, and slightly tweak it if this fails.

    Attempts to open the given filename. If this fails, it tries to change
    the filename slightly, step by step, until it's either able to open it
    or it fails and raises a final exception, like the standard open()
    function.

    It returns the tuple (stream, definitive_file_name).
    """
    try:
        if filename == u'-':
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            return (sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout, filename)
        stream = open(encodeFilename(filename), open_mode)
        return (stream, filename)
    except (IOError, OSError) as err:
        if err.errno in (errno.EACCES,):
            raise

        # In case of error, try to remove win32 forbidden chars
        alt_filename = os.path.join(
                        re.sub(u'[/<>:"\\|\\\\?\\*]', u'#', path_part)
                        for path_part in os.path.split(filename)
                       )
        if alt_filename == filename:
            raise
        else:
            # An exception here should be caught in the caller
            stream = open(encodeFilename(filename), open_mode)
            return (stream, alt_filename)


def timeconvert(timestr):
    """Convert RFC 2822 defined time string into system timestamp"""
    timestamp = None
    timetuple = email.utils.parsedate_tz(timestr)
    if timetuple is not None:
        timestamp = email.utils.mktime_tz(timetuple)
    return timestamp

def sanitize_filename(s, restricted=False, is_id=False):
    """Sanitizes a string so it could be used as part of a filename.
    If restricted is set, use a stricter subset of allowed characters.
    Set is_id if this is not an arbitrary string, but an ID that should be kept if possible
    """
    def replace_insane(char):
        if char == '?' or ord(char) < 32 or ord(char) == 127:
            return ''
        elif char == '"':
            return '' if restricted else '\''
        elif char == ':':
            return '_-' if restricted else ' -'
        elif char in '\\/|*<>':
            return '_'
        if restricted and (char in '!&\'()[]{}$;`^,#' or char.isspace()):
            return '_'
        if restricted and ord(char) > 127:
            return '_'
        return char

    result = u''.join(map(replace_insane, s))
    if not is_id:
        while '__' in result:
            result = result.replace('__', '_')
        result = result.strip('_')
        # Common case of "Foreign band name - English song title"
        if restricted and result.startswith('-_'):
            result = result[2:]
        if not result:
            result = '_'
    return result

def orderedSet(iterable):
    """ Remove all duplicates from the input iterable """
    res = []
    for el in iterable:
        if el not in res:
            res.append(el)
    return res

def unescapeHTML(s):
    """
    @param s a string
    """
    assert type(s) == type(u'')

    result = re.sub(u'(?u)&(.+?);', htmlentity_transform, s)
    return result

def encodeFilename(s):
    """
    @param s The name of the file
    """

    assert type(s) == type(u'')

    # Python 3 has a Unicode API
    if sys.version_info >= (3, 0):
        return s

    if sys.platform == 'win32' and sys.getwindowsversion()[0] >= 5:
        # Pass u'' directly to use Unicode APIs on Windows 2000 and up
        # (Detecting Windows NT 4 is tricky because 'major >= 4' would
        # match Windows 9x series as well. Besides, NT 4 is obsolete.)
        return s
    else:
        encoding = sys.getfilesystemencoding()
        if encoding is None:
            encoding = 'utf-8'
        return s.encode(encoding, 'ignore')

def decodeOption(optval):
    if optval is None:
        return optval
    if isinstance(optval, bytes):
        optval = optval.decode(preferredencoding())

    assert isinstance(optval, compat_str)
    return optval

def formatSeconds(secs):
    if secs > 3600:
        return '%d:%02d:%02d' % (secs // 3600, (secs % 3600) // 60, secs % 60)
    elif secs > 60:
        return '%d:%02d' % (secs // 60, secs % 60)
    else:
        return '%d' % secs

def make_HTTPS_handler(opts):
    if sys.version_info < (3,2):
        # Python's 2.x handler is very simplistic
        return compat_urllib_request.HTTPSHandler()
    else:
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.set_default_verify_paths()
        
        context.verify_mode = (ssl.CERT_NONE
                               if opts.no_check_certificate
                               else ssl.CERT_REQUIRED)
        return compat_urllib_request.HTTPSHandler(context=context)

class ExtractorError(Exception):
    """Error during info extraction."""
    def __init__(self, msg, tb=None, expected=False, cause=None):
        """ tb, if given, is the original traceback (so that it can be printed out).
        If expected is set, this is a normal error message and most likely not a bug in youtube-dl.
        """

        if sys.exc_info()[0] in (compat_urllib_error.URLError, socket.timeout, UnavailableVideoError):
            expected = True
        if not expected:
            msg = msg + u'; please report this issue on https://yt-dl.org/bug . Be sure to call youtube-dl with the --verbose flag and include its complete output. Make sure you are using the latest version; type  youtube-dl -U  to update.'
        super(ExtractorError, self).__init__(msg)

        self.traceback = tb
        self.exc_info = sys.exc_info()  # preserve original exception
        self.cause = cause

    def format_traceback(self):
        if self.traceback is None:
            return None
        return u''.join(traceback.format_tb(self.traceback))


class DownloadError(Exception):
    """Download Error exception.

    This exception may be thrown by FileDownloader objects if they are not
    configured to continue on errors. They will contain the appropriate
    error message.
    """
    def __init__(self, msg, exc_info=None):
        """ exc_info, if given, is the original exception that caused the trouble (as returned by sys.exc_info()). """
        super(DownloadError, self).__init__(msg)
        self.exc_info = exc_info


class SameFileError(Exception):
    """Same File exception.

    This exception will be thrown by FileDownloader objects if they detect
    multiple files would have to be downloaded to the same file on disk.
    """
    pass


class PostProcessingError(Exception):
    """Post Processing exception.

    This exception may be raised by PostProcessor's .run() method to
    indicate an error in the postprocessing task.
    """
    def __init__(self, msg):
        self.msg = msg

class MaxDownloadsReached(Exception):
    """ --max-downloads limit has been reached. """
    pass


class UnavailableVideoError(Exception):
    """Unavailable Format exception.

    This exception will be thrown when a video is requested
    in a format that is not available for that video.
    """
    pass


class ContentTooShortError(Exception):
    """Content Too Short exception.

    This exception may be raised by FileDownloader objects when a file they
    download is too small for what the server announced first, indicating
    the connection was probably interrupted.
    """
    # Both in bytes
    downloaded = None
    expected = None

    def __init__(self, downloaded, expected):
        self.downloaded = downloaded
        self.expected = expected

class YoutubeDLHandler(compat_urllib_request.HTTPHandler):
    """Handler for HTTP requests and responses.

    This class, when installed with an OpenerDirector, automatically adds
    the standard headers to every HTTP request and handles gzipped and
    deflated responses from web servers. If compression is to be avoided in
    a particular request, the original request in the program code only has
    to include the HTTP header "Youtubedl-No-Compression", which will be
    removed before making the real request.

    Part of this code was copied from:

    http://techknack.net/python-urllib2-handlers/

    Andrew Rowls, the author of that code, agreed to release it to the
    public domain.
    """

    @staticmethod
    def deflate(data):
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error:
            return zlib.decompress(data)

    @staticmethod
    def addinfourl_wrapper(stream, headers, url, code):
        if hasattr(compat_urllib_request.addinfourl, 'getcode'):
            return compat_urllib_request.addinfourl(stream, headers, url, code)
        ret = compat_urllib_request.addinfourl(stream, headers, url)
        ret.code = code
        return ret

    def http_request(self, req):
        for h,v in std_headers.items():
            if h in req.headers:
                del req.headers[h]
            req.add_header(h, v)
        if 'Youtubedl-no-compression' in req.headers:
            if 'Accept-encoding' in req.headers:
                del req.headers['Accept-encoding']
            del req.headers['Youtubedl-no-compression']
        if 'Youtubedl-user-agent' in req.headers:
            if 'User-agent' in req.headers:
                del req.headers['User-agent']
            req.headers['User-agent'] = req.headers['Youtubedl-user-agent']
            del req.headers['Youtubedl-user-agent']
        return req

    def http_response(self, req, resp):
        old_resp = resp
        # gzip
        if resp.headers.get('Content-encoding', '') == 'gzip':
            content = resp.read()
            gz = gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb')
            try:
                uncompressed = io.BytesIO(gz.read())
            except IOError as original_ioerror:
                # There may be junk add the end of the file
                # See http://stackoverflow.com/q/4928560/35070 for details
                for i in range(1, 1024):
                    try:
                        gz = gzip.GzipFile(fileobj=io.BytesIO(content[:-i]), mode='rb')
                        uncompressed = io.BytesIO(gz.read())
                    except IOError:
                        continue
                    break
                else:
                    raise original_ioerror
            resp = self.addinfourl_wrapper(uncompressed, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
        # deflate
        if resp.headers.get('Content-encoding', '') == 'deflate':
            gz = io.BytesIO(self.deflate(resp.read()))
            resp = self.addinfourl_wrapper(gz, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
        return resp

    https_request = http_request
    https_response = http_response

def unified_strdate(date_str):
    """Return a string with the date in the format YYYYMMDD"""
    upload_date = None
    #Replace commas
    date_str = date_str.replace(',',' ')
    # %z (UTC offset) is only supported in python>=3.2
    date_str = re.sub(r' (\+|-)[\d]*$', '', date_str)
    format_expressions = [
        '%d %B %Y',
        '%B %d %Y',
        '%b %d %Y',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%Y/%m/%d %H:%M:%S',
        '%d.%m.%Y %H:%M',
        '%Y-%m-%dT%H:%M:%SZ',
    ]
    for expression in format_expressions:
        try:
            upload_date = datetime.datetime.strptime(date_str, expression).strftime('%Y%m%d')
        except:
            pass
    return upload_date

def determine_ext(url, default_ext=u'unknown_video'):
    guess = url.partition(u'?')[0].rpartition(u'.')[2]
    if re.match(r'^[A-Za-z0-9]+$', guess):
        return guess
    else:
        return default_ext

def subtitles_filename(filename, sub_lang, sub_format):
    return filename.rsplit('.', 1)[0] + u'.' + sub_lang + u'.' + sub_format

def date_from_str(date_str):
    """
    Return a datetime object from a string in the format YYYYMMDD or
    (now|today)[+-][0-9](day|week|month|year)(s)?"""
    today = datetime.date.today()
    if date_str == 'now'or date_str == 'today':
        return today
    match = re.match('(now|today)(?P<sign>[+-])(?P<time>\d+)(?P<unit>day|week|month|year)(s)?', date_str)
    if match is not None:
        sign = match.group('sign')
        time = int(match.group('time'))
        if sign == '-':
            time = -time
        unit = match.group('unit')
        #A bad aproximation?
        if unit == 'month':
            unit = 'day'
            time *= 30
        elif unit == 'year':
            unit = 'day'
            time *= 365
        unit += 's'
        delta = datetime.timedelta(**{unit: time})
        return today + delta
    return datetime.datetime.strptime(date_str, "%Y%m%d").date()
    
class DateRange(object):
    """Represents a time interval between two dates"""
    def __init__(self, start=None, end=None):
        """start and end must be strings in the format accepted by date"""
        if start is not None:
            self.start = date_from_str(start)
        else:
            self.start = datetime.datetime.min.date()
        if end is not None:
            self.end = date_from_str(end)
        else:
            self.end = datetime.datetime.max.date()
        if self.start > self.end:
            raise ValueError('Date range: "%s" , the start date must be before the end date' % self)
    @classmethod
    def day(cls, day):
        """Returns a range that only contains the given day"""
        return cls(day,day)
    def __contains__(self, date):
        """Check if the date is in the range"""
        if not isinstance(date, datetime.date):
            date = date_from_str(date)
        return self.start <= date <= self.end
    def __str__(self):
        return '%s - %s' % ( self.start.isoformat(), self.end.isoformat())


def platform_name():
    """ Returns the platform name as a compat_str """
    res = platform.platform()
    if isinstance(res, bytes):
        res = res.decode(preferredencoding())

    assert isinstance(res, compat_str)
    return res


def write_string(s, out=None):
    if out is None:
        out = sys.stderr
    assert type(s) == type(u'')

    if ('b' in getattr(out, 'mode', '') or
            sys.version_info[0] < 3):  # Python 2 lies about mode of sys.stderr
        s = s.encode(preferredencoding(), 'ignore')
    out.write(s)
    out.flush()


def bytes_to_intlist(bs):
    if not bs:
        return []
    if isinstance(bs[0], int):  # Python 3
        return list(bs)
    else:
        return [ord(c) for c in bs]


def intlist_to_bytes(xs):
    if not xs:
        return b''
    if isinstance(chr(0), bytes):  # Python 2
        return ''.join([chr(x) for x in xs])
    else:
        return bytes(xs)


def get_cachedir(params={}):
    cache_root = os.environ.get('XDG_CACHE_HOME',
                                os.path.expanduser('~/.cache'))
    return params.get('cachedir', os.path.join(cache_root, 'youtube-dl'))
