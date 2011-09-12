from axl.axel import Event
from couchpotato.core.helpers.variable import mergeDicts
from couchpotato.core.logger import CPLog
import threading
import traceback

log = CPLog(__name__)
events = {}


def addEvent(name, handler, priority = 0):

    if events.get(name):
        e = events[name]
    else:
        e = events[name] = Event(threads = 20, exc_info = True, traceback = True, lock = threading.RLock())

    def createHandle(*args, **kwargs):

        try:
            parent = handler.im_self
            parent.beforeCall(handler)
            h = handler(*args, **kwargs)
            parent.afterCall(handler)
        except:
            h = handler(*args, **kwargs)

        return h

    if name == 'app.initialize':
        print 'test', priority

    e.handle(createHandle, priority = priority)

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
            results = None

            # Loop over results, stop when first not None result is found.
            for r in result:
                if r[0] is True and r[1] is not None:
                    results = r[1]
                    break
                elif r[1]:
                    errorHandler(r[1])
                else:
                    log.debug('Assume disabled plugin: %s' % r[2])

        else:
            results = []
            for r in result:
                if r[0] == True and r[1]:
                    results.append(r[1])
                elif r[1]:
                    errorHandler(r[1])

            # Merge
            if merge and len(results) > 0:
                # Dict
                if type(results[0]) == dict:
                    merged = {}
                    for result in results:
                        merged = mergeDicts(merged, result)

                    results = merged
                # Lists
                elif type(results[0]) == list:
                    merged = []
                    for result in results:
                        merged += result

                    results = merged

        return results
    except KeyError, e:
        pass
    except Exception:
        log.error('%s: %s' % (name, traceback.format_exc()))

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
