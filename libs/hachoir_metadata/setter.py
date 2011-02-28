from datetime import date, datetime
import re
from hachoir_core.language import Language
from locale import setlocale, LC_ALL
from time import strptime
from hachoir_metadata.timezone import createTimezone
from hachoir_metadata import config

NORMALIZE_REGEX = re.compile("[-/.: ]+")
YEAR_REGEX1 = re.compile("^([0-9]{4})$")

# Date regex: YYYY-MM-DD (US format)
DATE_REGEX1 = re.compile("^([0-9]{4})~([01][0-9])~([0-9]{2})$")

# Date regex: YYYY-MM-DD HH:MM:SS (US format)
DATETIME_REGEX1 = re.compile("^([0-9]{4})~([01][0-9])~([0-9]{2})~([0-9]{1,2})~([0-9]{2})~([0-9]{2})$")

# Datetime regex: "MM-DD-YYYY HH:MM:SS" (FR format)
DATETIME_REGEX2 = re.compile("^([01]?[0-9])~([0-9]{2})~([0-9]{4})~([0-9]{1,2})~([0-9]{2})~([0-9]{2})$")

# Timezone regex: "(...) +0200"
TIMEZONE_REGEX = re.compile("^(.*)~([+-][0-9]{2})00$")

# Timestmap: 'February 2007'
MONTH_YEAR = "%B~%Y"

# Timestmap: 'Sun Feb 24 15:51:09 2008'
RIFF_TIMESTAMP = "%a~%b~%d~%H~%M~%S~%Y"

# Timestmap: 'Thu, 19 Jul 2007 09:03:57'
ISO_TIMESTAMP = "%a,~%d~%b~%Y~%H~%M~%S"

def parseDatetime(value):
    """
    Year and date:
    >>> parseDatetime("2000")
    (datetime.date(2000, 1, 1), u'2000')
    >>> parseDatetime("2004-01-02")
    datetime.date(2004, 1, 2)

    Timestamp:
    >>> parseDatetime("2004-01-02 18:10:45")
    datetime.datetime(2004, 1, 2, 18, 10, 45)
    >>> parseDatetime("2004-01-02 18:10:45")
    datetime.datetime(2004, 1, 2, 18, 10, 45)

    Timestamp with timezone:
    >>> parseDatetime(u'Thu, 19 Jul 2007 09:03:57 +0000')
    datetime.datetime(2007, 7, 19, 9, 3, 57, tzinfo=<TimezoneUTC delta=0, name=u'UTC'>)
    >>> parseDatetime(u'Thu, 19 Jul 2007 09:03:57 +0200')
    datetime.datetime(2007, 7, 19, 9, 3, 57, tzinfo=<Timezone delta=2:00:00, name='+0200'>)
    """
    value = NORMALIZE_REGEX.sub("~", value.strip())
    regs = YEAR_REGEX1.match(value)
    if regs:
        try:
            year = int(regs.group(1))
            return (date(year, 1, 1), unicode(year))
        except ValueError:
            pass
    regs = DATE_REGEX1.match(value)
    if regs:
        try:
            year = int(regs.group(1))
            month = int(regs.group(2))
            day = int(regs.group(3))
            return date(year, month, day)
        except ValueError:
            pass
    regs = DATETIME_REGEX1.match(value)
    if regs:
        try:
            year = int(regs.group(1))
            month = int(regs.group(2))
            day = int(regs.group(3))
            hour = int(regs.group(4))
            min = int(regs.group(5))
            sec = int(regs.group(6))
            return datetime(year, month, day, hour, min, sec)
        except ValueError:
            pass
    regs = DATETIME_REGEX2.match(value)
    if regs:
        try:
            month = int(regs.group(1))
            day = int(regs.group(2))
            year = int(regs.group(3))
            hour = int(regs.group(4))
            min = int(regs.group(5))
            sec = int(regs.group(6))
            return datetime(year, month, day, hour, min, sec)
        except ValueError:
            pass
    current_locale = setlocale(LC_ALL, "C")
    try:
        match = TIMEZONE_REGEX.match(value)
        if match:
            without_timezone = match.group(1)
            delta = int(match.group(2))
            delta = createTimezone(delta)
        else:
            without_timezone = value
            delta = None
        try:
            timestamp = strptime(without_timezone, ISO_TIMESTAMP)
            arguments = list(timestamp[0:6]) + [0, delta]
            return datetime(*arguments)
        except ValueError:
            pass

        try:
            timestamp = strptime(without_timezone, RIFF_TIMESTAMP)
            arguments = list(timestamp[0:6]) + [0, delta]
            return datetime(*arguments)
        except ValueError:
            pass

        try:
            timestamp = strptime(value, MONTH_YEAR)
            arguments = list(timestamp[0:3])
            return date(*arguments)
        except ValueError:
            pass
    finally:
        setlocale(LC_ALL, current_locale)
    return None

def setDatetime(meta, key, value):
    if isinstance(value, (str, unicode)):
        return parseDatetime(value)
    elif isinstance(value, (date, datetime)):
        return value
    return None

def setLanguage(meta, key, value):
    """
    >>> setLanguage(None, None, "fre")
    <Language 'French', code='fre'>
    >>> setLanguage(None, None, u"ger")
    <Language 'German', code='ger'>
    """
    return Language(value)

def setTrackTotal(meta, key, total):
    """
    >>> setTrackTotal(None, None, "10")
    10
    """
    try:
        return int(total)
    except ValueError:
        meta.warning("Invalid track total: %r" % total)
        return None

def setTrackNumber(meta, key, number):
    if isinstance(number, (int, long)):
        return number
    if "/" in number:
        number, total = number.split("/", 1)
        meta.track_total = total
    try:
        return int(number)
    except ValueError:
        meta.warning("Invalid track number: %r" % number)
        return None

def normalizeString(text):
    if config.RAW_OUTPUT:
        return text
    return text.strip(" \t\v\n\r\0")

