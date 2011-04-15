from axl.axel import Event
from couchpotato.core.helpers.variable import merge_dicts
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
    #log.debug('Firing "%s": %s, %s' % (name, args, kwargs))
    try:

        # Return single handler
        single = False
        try:
            del kwargs['single']
            single = True
        except: pass

        # Merge items
        merge = False
        try:
            del kwargs['merge']
            merge = True
        except: pass

        e = events[name]
        e.asynchronous = False
        result = e(*args, **kwargs)

        if single and not merge:
            results = result[0][1]
        else:
            results = []
            for r in result:
                if r[0] == True:
                    results.append(r[1])
                else:
                    errorHandler(r[1])

            # Merge the results
            if merge:
                merged = {}
                for result in results:
                    merged = merge_dicts(merged, result)

                results = merged

        return results
    except Exception, e:
        log.error('%s: %s' % (name, e))

def fireEventAsync(name, *args, **kwargs):
    #log.debug('Async "%s": %s, %s' % (name, args, kwargs))
    try:
        e = events[name]
        e.asynchronous = True
        e.error_handler = errorHandler

        e(*args, **kwargs)
        return True
    except Exception, e:
        log.error('%s: %s' % (name, e))

def errorHandler(error):
    etype, value, tb = error
    log.error(''.join(traceback.format_exception(etype, value, tb)))

def getEvent(name):
    return events[name]
