from couchpotato.core.logger import CPLog
from axl.axel import Event

log = CPLog(__name__)
events = {}

def addEvent(name, handler):

    if events.get(name):
        e = events[name]
    else:
        e = events[name] = Event(threads = 20, exc_info = True, traceback = True)

    e += handler

def removeEvent(name, handler):
    e = events[name]
    e -= handler

def fireEvent(name, *args, **kwargs):
    try:
        e = events[name]
        e.asynchronous = False
        return e(*args, **kwargs)
    except Exception, e:
        log.debug(e)

def fireEventAsync(name, *args, **kwargs):
    try:
        e = events[name]
        e.asynchronous = True
        return e(*args, **kwargs)
    except Exception, e:
        log.debug(e)

def getEvent(name):
    return events[name]
