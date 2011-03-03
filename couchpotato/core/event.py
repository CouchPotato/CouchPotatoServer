from axl.axel import Event
from couchpotato.core.logger import CPLog
import traceback

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
        result = e(*args, **kwargs)

        results = []
        for r in result:
            if r[0] == True:
                results.append(r[1])
            else:
                etype, value, tb = r[1]
                log.debug(''.join(traceback.format_exception(etype, value, tb)))

        return results
    except Exception, e:
        log.debug(e)

def fireEventAsync(name, *args, **kwargs):
    try:
        e = events[name]
        e.asynchronous = True
        e(*args, **kwargs)
        return True
    except Exception, e:
        log.debug(e)

def getEvent(name):
    return events[name]
