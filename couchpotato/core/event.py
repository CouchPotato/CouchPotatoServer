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
        log.error('Error in event "%s", that wasn\'t caught: %s%s', (name, traceback.format_exc(), Env.all() if not Env.get('dev') else ''))


def addEvent(name, handler, priority = 100):

    if not events.get(name):
        events[name] = []

    def createHandle(*args, **kwargs):

        h = None
        try:
            # Open handler
            has_parent = hasattr(handler, 'im_self')
            parent = None
            if has_parent:
                parent = handler.__self__
                bc = hasattr(parent, 'beforeCall')
                if bc: parent.beforeCall(handler)

            # Main event
            h = runHandler(name, handler, *args, **kwargs)

            # Close handler
            if parent and has_parent:
                ac = hasattr(parent, 'afterCall')
                if ac: parent.afterCall(handler)
        except:
            log.error('Failed creating handler %s %s: %s', (name, handler, traceback.format_exc()))

        return h

    events[name].append({
        'handler': createHandle,
        'priority': priority,
    })


def removeEvent(name, handler):
    e = events[name]
    e -= handler


def fireEvent(name, *args, **kwargs):
    if name not in events: return

    #log.debug('Firing event %s', name)
    try:

        options = {
            'is_after_event': False,  # Fire after event
            'on_complete': False,  # onComplete event
            'single': False,  # Return single handler
            'merge': False,  # Merge items
            'in_order': False,  # Fire them in specific order, waits for the other to finish
        }

        # Do options
        for x in options:
            try:
                val = kwargs[x]
                del kwargs[x]
                options[x] = val
            except: pass

        if len(events[name]) == 1:

            single = None
            try:
                single = events[name][0]['handler'](*args, **kwargs)
            except:
                log.error('Failed running single event: %s', traceback.format_exc())

            # Don't load thread for single event
            result = {
                'single': (single is not None, single),
            }

        else:

            e = Event(name = name, threads = 10, exc_info = True, traceback = True, lock = threading.RLock())

            for event in events[name]:
                e.handle(event['handler'], priority = event['priority'])

            # Make sure only 1 event is fired at a time when order is wanted
            kwargs['event_order_lock'] = threading.RLock() if options['in_order'] or options['single'] else None
            kwargs['event_return_on_result'] = options['single']

            # Fire
            result = e(*args, **kwargs)

        result_keys = result.keys()
        result_keys.sort(natcmp)

        if options['single'] and not options['merge']:
            results = None

            # Loop over results, stop when first not None result is found.
            for r_key in result_keys:
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
            for r_key in result_keys:
                r = result[r_key]
                if r[0] == True and r[1]:
                    results.append(r[1])
                elif r[1]:
                    errorHandler(r[1])

            # Merge
            if options['merge'] and len(results) > 0:

                # Dict
                if isinstance(results[0], dict):
                    results.reverse()

                    merged = {}
                    for result in results:
                        merged = mergeDicts(merged, result, prepend_list = True)

                    results = merged
                # Lists
                elif isinstance(results[0], list):
                    merged = []
                    for result in results:
                        if result not in merged:
                            merged += result

                    results = merged

        modified_results = fireEvent('result.modify.%s' % name, results, single = True)
        if modified_results:
            log.debug('Return modified results for %s', name)
            results = modified_results

        if not options['is_after_event']:
            fireEvent('%s.after' % name, is_after_event = True)

        if options['on_complete']:
            options['on_complete']()

        return results
    except Exception:
        log.error('%s: %s', (name, traceback.format_exc()))


def fireEventAsync(*args, **kwargs):
    try:
        t = threading.Thread(target = fireEvent, args = args, kwargs = kwargs)
        t.setDaemon(True)
        t.start()
        return True
    except Exception as e:
        log.error('%s: %s', (args[0], e))


def errorHandler(error):
    etype, value, tb = error
    log.error(''.join(traceback.format_exception(etype, value, tb)))


def getEvent(name):
    return events[name]
