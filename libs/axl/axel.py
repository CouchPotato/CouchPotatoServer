# axel.py
#
# Copyright (C) 2010 Adrian Cristea adrian dot cristea at gmail dotcom
#
# Based on an idea by Peter Thatcher, found on
# http://www.valuedlessons.com/2008/04/events-in-python.html
#
# This module is part of Axel and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php 
#
# Source: http://pypi.python.org/pypi/axel
# Docs:   http://packages.python.org/axel

import sys, threading, Queue

class Event(object):
    """ 
    Event object inspired by C# events. Handlers can be registered and
    unregistered using += and -= operators. Execution and result are  
    influenced by the arguments passed to the constructor and += method.
        
    from axel import Event
     
    event = Event()
    def on_event(*args, **kwargs):
        return (args, kwargs)
    
    event += on_event                        # handler registration
    print(event(10, 20, y=30))        
    >> ((True, ((10, 20), {'y': 30}), <function on_event at 0x00BAA270>),)
     
    event -= on_event                        # handler is unregistered
    print(event(10, 20, y=30))     
    >> None
     
    class Mouse(object):
        def __init__(self):
            self.click = Event(self)
            self.click += self.on_click      # handler registration
    
        def on_click(self, sender, *args, **kwargs):
            assert isinstance(sender, Mouse), 'Wrong sender'
            return (args, kwargs)
    
    mouse = Mouse()
    print(mouse.click(10, 20))        
    >> ((True, ((10, 20), {}), 
    >>  <bound method Mouse.on_click of <__main__.Mouse object at 0x00B6F470>>),)
    
    mouse.click -= mouse.on_click            # handler is unregistered
    print(mouse.click(10, 20))                        
    >> None
    """

    def __init__(self, sender = None, asynch = False, exc_info = False,
                 lock = None, threads = 3, traceback = False):
        """ Creates an event 
        
        asynch
            if True handler's are executes asynchronous
        exc_info
            if True, result will contain sys.exc_info()[:2] on error
        lock
            threading.RLock used to synchronize execution
        sender
            event's sender. The sender is passed as the first argument to the 
            handler, only if is not None. For this case the handler must have
            a placeholder in the arguments to receive the sender
        threads
            maximum number of threads that will be started
        traceback
            if True, the execution result will contain sys.exc_info() 
            on error. exc_info must be also True to get the traceback      
                
        hash = hash(handler)
        
        Handlers are stored in a dictionary that has as keys the handler's hash        
            handlers = { 
                hash : (handler, memoize, timeout),
                hash : (handler, memoize, timeout), ... 
            }
        The execution result is cached using the following structure    
            memoize = { 
                hash : ((args, kwargs, result), (args, kwargs, result), ...), 
                hash : ((args, kwargs, result), ...), ...                      
            } 
        The execution result is returned as a tuple having this structure
            exec_result = (
                (True, result, handler),        # on success
                (False, error_info, handler),   # on error 
                (None, None, handler), ...      # asynchronous execution
            )
        """
        self.asynchronous = asynch
        self.exc_info = exc_info
        self.lock = lock
        self.sender = sender
        self.threads = threads
        self.traceback = traceback
        self.handlers = {}
        self.memoize = {}

    def handle(self, handler):
        """ Registers a handler. The handler can be transmitted together 
        with two arguments as a list or dictionary. The arguments are:
        
        memoize 
            if True, the execution result will be cached in self.memoize
        timeout 
            will allocate a predefined time interval for the execution
            
        If arguments are provided as a list, they are considered to have 
        this sequence: (handler, memoize, timeout)                
        
        Examples:
            event += handler    
            event += (handler, True, 1.5)
            event += {'handler':handler, 'memoize':True, 'timeout':1.5}         
        """
        handler_, memoize, timeout = self._extract(handler)
        self.handlers[hash(handler_)] = (handler_, memoize, timeout)
        return self

    def unhandle(self, handler):
        """ Unregisters a handler """
        handler_, memoize, timeout = self._extract(handler)
        key = hash(handler_)
        if not key in self.handlers:
            raise ValueError('Handler "%s" was not found' % str(handler_))
        del self.handlers[key]
        return self

    def fire(self, *args, **kwargs):
        """ Stores all registered handlers in a queue for processing """
        self.queue = Queue.Queue()
        self.result = []

        if self.handlers:
            max_threads = self._threads()

            for i in range(max_threads):
                t = threading.Thread(target = self._execute,
                                     args = args, kwargs = kwargs)
                t.daemon = True
                t.start()

            for handler in self.handlers:
                self.queue.put(handler)

                if self.asynchronous:
                    handler_, memoize, timeout = self.handlers[handler]
                    self.result.append((None, None, handler_))

            if not self.asynchronous:
                self.queue.join()

        return tuple(self.result) or None

    def count(self):
        """ Returns the count of registered handlers """
        return len(self.handlers)

    def clear(self):
        """ Discards all registered handlers and cached results """
        self.handlers.clear()
        self.memoize.clear()

    def _execute(self, *args, **kwargs):
        """ Executes all handlers stored in the queue """
        while True:
            try:
                handler, memoize, timeout = self.handlers[self.queue.get()]

                if isinstance(self.lock, threading._RLock):
                    self.lock.acquire() #synchronization

                try:
                    r = self._memoize(memoize, timeout, handler, *args, **kwargs)
                    if not self.asynchronous:
                        self.result.append(tuple(r))

                except Exception:
                    if not self.asynchronous:
                        self.result.append((False, self._error(sys.exc_info()),
                                            handler))
                finally:
                    if isinstance(self.lock, threading._RLock):
                        self.lock.release()

                    if not self.asynchronous:
                        self.queue.task_done()

                    if self.queue.empty():
                        raise Queue.Empty

            except Queue.Empty:
                break

    def _extract(self, queue_item):
        """ Extracts a handler and handler's arguments that can be provided 
        as list or dictionary. If arguments are provided as list, they are 
        considered to have this sequence: (handler, memoize, timeout)                
        Examples:
            event += handler
            event += (handler, True, 1.5)
            event += {'handler':handler, 'memoize':True, 'timeout':1.5}
        """
        assert queue_item, 'Invalid list of arguments'
        handler = None
        memoize = False
        timeout = 0

        if not isinstance(queue_item, (list, tuple, dict)):
            handler = queue_item
        elif isinstance(queue_item, (list, tuple)):
            if len(queue_item) == 3:
                handler, memoize, timeout = queue_item
            elif len(queue_item) == 2:
                handler, memoize, = queue_item
            elif len(queue_item) == 1:
                handler = queue_item
        elif isinstance(queue_item, dict):
            handler = queue_item.get('handler')
            memoize = queue_item.get('memoize', False)
            timeout = queue_item.get('timeout', 0)
        return (handler, bool(memoize), float(timeout))

    def _memoize(self, memoize, timeout, handler, *args, **kwargs):
        """ Caches the execution result of successful executions        
        hash = hash(handler)
        memoize = { 
            hash : ((args, kwargs, result), (args, kwargs, result), ...), 
            hash : ((args, kwargs, result), ...), ...                       
        }
        """
        if not isinstance(handler, Event) and self.sender is not None:
            args = list(args)[:]
            args.insert(0, self.sender)

        if not memoize:
            if timeout <= 0:    #no time restriction
                return [True, handler(*args, **kwargs), handler]

            result = self._timeout(timeout, handler, *args, **kwargs)
            if isinstance(result, tuple) and len(result) == 3:
                if isinstance(result[1], Exception): #error occurred
                    return [False, self._error(result), handler]
            return [True, result, handler]
        else:
            hash_ = hash(handler)
            if hash_ in self.memoize:
                for args_, kwargs_, result in self.memoize[hash_]:
                    if args_ == args and kwargs_ == kwargs:
                        return [True, result, handler]

            if timeout <= 0:    #no time restriction
                result = handler(*args, **kwargs)
            else:
                result = self._timeout(timeout, handler, *args, **kwargs)
                if isinstance(result, tuple) and len(result) == 3:
                    if isinstance(result[1], Exception): #error occurred
                        return [False, self._error(result), handler]

            lock = threading.RLock()
            lock.acquire()
            try:
                if hash_ not in self.memoize:
                    self.memoize[hash_] = []
                self.memoize[hash_].append((args, kwargs, result))
                return [True, result, handler]
            finally:
                lock.release()


    def _timeout(self, timeout, handler, *args, **kwargs):
        """ Controls the time allocated for the execution of a method """
        t = spawn_thread(target = handler, args = args, kwargs = kwargs)
        t.daemon = True
        t.start()
        t.join(timeout)

        if not t.is_alive():
            if t.exc_info:
                return t.exc_info
            return t.result
        else:
            try:
                msg = '[%s] Execution was forcefully terminated'
                raise RuntimeError(msg % t.name)
            except:
                return sys.exc_info()

    def _threads(self):
        """ Calculates maximum number of threads that will be started """
        if self.threads < len(self.handlers):
            return self.threads
        return len(self.handlers)

    def _error(self, exc_info):
        """ Retrieves the error info """
        if self.exc_info:
            if self.traceback:
                return exc_info
            return exc_info[:2]
        return exc_info[1]

    __iadd__ = handle
    __isub__ = unhandle
    __call__ = fire
    __len__ = count

class spawn_thread(threading.Thread):
    """ Spawns a new thread and returns the execution result """

    def __init__(self, target, args = (), kwargs = {}, default = None):
        threading.Thread.__init__(self)
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self.result = default
        self.exc_info = None

    def run(self):
        try:
            self.result = self._target(*self._args, **self._kwargs)
        except:
            self.exc_info = sys.exc_info()
        finally:
            del self._target, self._args, self._kwargs
