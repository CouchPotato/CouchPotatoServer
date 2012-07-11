from axl.axel import Event
from couchpotato.core.helpers.variable import mergeDicts, natcmp
from couchpotato.core.logger import CPLog
import threading
import traceback

log = CPLog(__name__)
events = {}

def runHandler(name, handler, *args, **kwargs):
    try:
        return handler(*args, **kwargs)
    except:
        from couchpotato.environment import Env
        log.error('Error in event "%s", that wasn\'t caught: %s%s', (name, traceback.format_exc(), Env.all()))

def addEvent(name, handler, priority = 100):

    if events.get(name):
        e = events[name]
    else:
        e = events[name] = Event(name = name, threads = 20, exc_info = True, traceback = True, lock = threading.RLock())

    def createHandle(*args, **kwargs):

        try:
            parent = handler.im_self
            bc = hasattr(parent, 'beforeCall')
            if bc: parent.beforeCall(handler)
            h = runHandler(name, handler, *args, **kwargs)
            ac = hasattr(parent, 'afterCall')
            if ac: parent.afterCall(handler)
        except:
            h = runHandler(name, handler, *args, **kwargs)

        return h

    e.handle(createHandle, priority = priority)

def removeEvent(name, handler):
    e = events[name]
    e -= handler

def fireEvent(name, *args, **kwargs):
    if not events.get(name): return
    #log.debug('Firing event %s', name)
    try:

        # Fire after event
        is_after_event = False
        try:
            del kwargs['is_after_event']
            is_after_event = True
        except: pass

        # onComplete event
        on_complete = False
        try:
            on_complete = kwargs['on_complete']
            del kwargs['on_complete']
        except: pass

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

        # Merge items
        in_order = False
        try:
            del kwargs['in_order']
            in_order = True
        except: pass

        e = events[name]
        if not in_order: e.lock.acquire()
        e.asynchronous = False
        e.in_order = in_order
        result = e(*args, **kwargs)
        if not in_order: e.lock.release()

        if single and not merge:
            results = None

            # Loop over results, stop when first not None result is found.
            for r_key in sorted(result.iterkeys(), cmp = natcmp):
                r = result[r_key]
                if r[0] is True and r[1] is not None:
                    results = r[1]
                    break
                elif r[1]:
                    errorHandler(r[1])
                else:
                    log.debug('Assume disabled eventhandler for: %s', name)

        else:
            results = []
            for r_key in sorted(result.iterkeys(), cmp = natcmp):
                r = result[r_key]
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

        modified_results = fireEvent('result.modify.%s' % name, results, single = True)
        if modified_results:
            log.debug('Return modified results for %s', name)
            results = modified_results

        if not is_after_event:
            fireEvent('%s.after' % name, is_after_event = True)

        if on_complete:
            on_complete()

        return results
    except KeyError, e:
        pass
    except Exception:
        log.error('%s: %s', (name, traceback.format_exc()))

def fireEventAsync(*args, **kwargs):
    try:
        my_thread = threading.Thread(target = fireEvent, args = args, kwargs = kwargs)
        my_thread.setDaemon(True)
        my_thread.start()
        return True
    except Exception, e:
        log.error('%s: %s', (args[0], e))

def errorHandler(error):
    etype, value, tb = error
    log.error(''.join(traceback.format_exception(etype, value, tb)))

def getEvent(name):
    return events[name]
