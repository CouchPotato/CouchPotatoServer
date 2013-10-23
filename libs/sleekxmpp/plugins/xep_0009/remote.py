"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Dann Martens (TOMOTON).
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from binding import py2xml, xml2py, xml2fault, fault2xml
from threading import RLock
import abc
import inspect
import logging
import sleekxmpp
import sys
import threading
import traceback

log = logging.getLogger(__name__)

def _intercept(method, name, public):
    def _resolver(instance, *args, **kwargs):
        log.debug("Locally calling %s.%s with arguments %s.", instance.FQN(), method.__name__, args)
        try:
            value = method(instance, *args, **kwargs)
            if value == NotImplemented:
                raise InvocationException("Local handler does not implement %s.%s!" % (instance.FQN(), method.__name__))
            return value
        except InvocationException:
            raise
        except Exception as e:
            raise InvocationException("A problem occured calling %s.%s!" % (instance.FQN(), method.__name__), e)
    _resolver._rpc = public
    _resolver._rpc_name = method.__name__ if name is None else name
    return _resolver

def remote(function_argument, public = True):
    '''
    Decorator for methods which are remotely callable. This decorator
    works in conjunction with classes which extend ABC Endpoint.
    Example:

        @remote
        def remote_method(arg1, arg2)

    Arguments:
        function_argument -- a stand-in for either the actual method
            OR a new name (string) for the method. In that case the
            method is considered mapped:
            Example:

            @remote("new_name")
            def remote_method(arg1, arg2)

        public -- A flag which indicates if this method should be part
            of the known dictionary of remote methods. Defaults to True.
            Example:

            @remote(False)
            def remote_method(arg1, arg2)

    Note: renaming and revising (public vs. private) can be combined.
    Example:

            @remote("new_name", False)
            def remote_method(arg1, arg2)
    '''
    if hasattr(function_argument, '__call__'):
        return _intercept(function_argument, None, public)
    else:
        if not isinstance(function_argument, basestring):
            if not isinstance(function_argument, bool):
                raise Exception('Expected an RPC method name or visibility modifier!')
            else:
                def _wrap_revised(function):
                    function = _intercept(function, None, function_argument)
                    return function
                return _wrap_revised
        def _wrap_remapped(function):
            function = _intercept(function, function_argument, public)
            return function
        return _wrap_remapped


class ACL:
    '''
    An Access Control List (ACL) is a list of rules, which are evaluated
    in order until a match is found. The policy of the matching rule
    is then applied.

    Rules are 3-tuples, consisting of a policy enumerated type, a JID
    expression and a RCP resource expression.

    Examples:
    [ (ACL.ALLOW, '*', '*') ] allow everyone everything, no restrictions
    [ (ACL.DENY, '*', '*') ] deny everyone everything, no restrictions
    [ (ACL.ALLOW, 'test@xmpp.org/unit', 'test.*'),
      (ACL.DENY, '*', '*') ] deny everyone everything, except named
        JID, which is allowed access to endpoint 'test' only.

    The use of wildcards is allowed in expressions, as follows:
    '*' everyone, or everything (= all endpoints and methods)
    'test@xmpp.org/*' every JID regardless of JID resource
    '*@xmpp.org/rpc' every JID from domain xmpp.org with JID res 'rpc'
    'frank@*' every 'frank', regardless of domain or JID res
    'system.*' all methods of endpoint 'system'
    '*.reboot' all methods reboot regardless of endpoint
    '''
    ALLOW = True
    DENY = False

    @classmethod
    def check(cls, rules, jid, resource):
        if rules is None:
            return cls.DENY                  # No rules means no access!
        jid = str(jid)     # Check the string representation of the JID.
        if not jid:
            return cls.DENY                  # Can't check an empty JID.
        for rule in rules:
            policy = cls._check(rule, jid, resource)
            if policy is not None:
                return policy
        return cls.DENY   # By default if not rule matches, deny access.

    @classmethod
    def _check(cls, rule, jid, resource):
        if cls._match(jid, rule[1]) and cls._match(resource, rule[2]):
            return rule[0]
        else:
            return None

    @classmethod
    def _next_token(cls, expression, index):
        new_index = expression.find('*', index)
        if new_index == 0:
            return ''
        else:
            if new_index == -1:
                return expression[index : ]
            else:
                return expression[index : new_index]

    @classmethod
    def _match(cls, value, expression):
        #! print "_match [VALUE] %s [EXPR] %s" % (value, expression)
        index = 0
        position = 0
        while index < len(expression):
            token = cls._next_token(expression, index)
            #! print "[TOKEN] '%s'" % token
            size = len(token)
            if size > 0:
                token_index = value.find(token, position)
                if token_index == -1:
                    return False
                else:
                    #! print "[INDEX-OF] %s" % token_index
                    position = token_index + len(token)
                pass
            if size == 0:
                index += 1
            else:
                index += size
        #! print "index %s position %s" % (index, position)
        return True

ANY_ALL = [ (ACL.ALLOW, '*', '*') ]


class RemoteException(Exception):
    '''
    Base exception for RPC. This exception is raised when a problem
    occurs in the network layer.
    '''

    def __init__(self, message="", cause=None):
        '''
        Initializes a new RemoteException.

        Arguments:
            message -- The message accompanying this exception.
            cause -- The underlying cause of this exception.
        '''
        self._message = message
        self._cause = cause
        pass

    def __str__(self):
        return repr(self._message)

    def get_message(self):
        return self._message

    def get_cause(self):
        return self._cause



class InvocationException(RemoteException):
    '''
    Exception raised when a problem occurs during the remote invocation
    of a method.
    '''
    pass



class AuthorizationException(RemoteException):
    '''
    Exception raised when the caller is not authorized to invoke the
    remote method.
    '''
    pass


class TimeoutException(Exception):
    '''
    Exception raised when the synchronous execution of a method takes
    longer than the given threshold because an underlying asynchronous
    reply did not arrive in time.
    '''
    pass


class Callback(object):
    '''
    A base class for callback handlers.
    '''
    __metaclass__ = abc.ABCMeta


    @abc.abstractproperty
    def set_value(self, value):
        return NotImplemented

    @abc.abstractproperty
    def cancel_with_error(self, exception):
        return NotImplemented


class Future(Callback):
    '''
    Represents the result of an asynchronous computation.
    '''

    def __init__(self):
        '''
        Initializes a new Future.
        '''
        self._value = None
        self._exception = None
        self._event = threading.Event()
        pass

    def set_value(self, value):
        '''
        Sets the value of this Future. Once the value is set, a caller
        blocked on get_value will be able to continue.
        '''
        self._value = value
        self._event.set()

    def get_value(self, timeout=None):
        '''
        Gets the value of this Future. This call will block until
        the result is available, or until an optional timeout expires.
        When this Future is cancelled with an error,

        Arguments:
            timeout -- The maximum waiting time to obtain the value.
        '''
        self._event.wait(timeout)
        if self._exception:
            raise self._exception
        if not self._event.is_set():
            raise TimeoutException
        return self._value

    def is_done(self):
        '''
        Returns true if a value has been returned.
        '''
        return self._event.is_set()

    def cancel_with_error(self, exception):
        '''
        Cancels the Future because of an error. Once cancelled, a
        caller blocked on get_value will be able to continue.
        '''
        self._exception = exception
        self._event.set()



class Endpoint(object):
    '''
    The Endpoint class is an abstract base class for all objects
    participating in an RPC-enabled XMPP network.

    A user subclassing this class is required to implement the method:
        FQN(self)
    where FQN stands for Fully Qualified Name, an unambiguous name
    which specifies which object an RPC call refers to. It is the
    first part in a RPC method name '<fqn>.<method>'.
    '''
    __metaclass__ = abc.ABCMeta


    def __init__(self, session, target_jid):
        '''
        Initialize a new Endpoint. This constructor should never be
        invoked by a user, instead it will be called by the factories
        which instantiate the RPC-enabled objects, of which only
        the classes are provided by the user.

        Arguments:
            session -- An RPC session instance.
            target_jid -- the identity of the remote XMPP entity.
        '''
        self.session = session
        self.target_jid = target_jid

    @abc.abstractproperty
    def FQN(self):
        return NotImplemented

    def get_methods(self):
        '''
        Returns a dictionary of all RPC method names provided by this
        class. This method returns the actual  method names as found
        in the class definition which have been decorated with:

            @remote
            def some_rpc_method(arg1, arg2)


        Unless:
            (1) the name has been remapped, in which case the new
                name will be returned.

                    @remote("new_name")
                    def some_rpc_method(arg1, arg2)

            (2) the method is set to hidden

                    @remote(False)
                    def some_hidden_method(arg1, arg2)
        '''
        result = dict()
        for function in dir(self):
            test_attr = getattr(self, function, None)
            try:
                if test_attr._rpc:
                    result[test_attr._rpc_name] = test_attr
            except Exception:
                pass
        return result



class Proxy(Endpoint):
    '''
    Implementation of the Proxy pattern which is intended to wrap
    around Endpoints in order to intercept calls, marshall them and
    forward them to the remote object.
    '''

    def __init__(self, endpoint, callback = None):
        '''
        Initializes a new Proxy.

        Arguments:
            endpoint -- The endpoint which is proxified.
        '''
        self._endpoint = endpoint
        self._callback = callback

    def __getattribute__(self, name, *args):
        if name in ('__dict__', '_endpoint', 'async', '_callback'):
            return object.__getattribute__(self, name)
        else:
            attribute = self._endpoint.__getattribute__(name)
            if hasattr(attribute, '__call__'):
                try:
                    if attribute._rpc:
                        def _remote_call(*args, **kwargs):
                            log.debug("Remotely calling '%s.%s' with arguments %s.", self._endpoint.FQN(), attribute._rpc_name, args)
                            return self._endpoint.session._call_remote(self._endpoint.target_jid, "%s.%s" % (self._endpoint.FQN(), attribute._rpc_name), self._callback, *args, **kwargs)
                        return _remote_call
                except:
                    pass   # If the attribute doesn't exist, don't care!
            return attribute

    def async(self, callback):
        return Proxy(self._endpoint, callback)

    def get_endpoint(self):
        '''
        Returns the proxified endpoint.
        '''
        return self._endpoint

    def FQN(self):
        return self._endpoint.FQN()


class JabberRPCEntry(object):


    def __init__(self, endpoint_FQN, call):
        self._endpoint_FQN = endpoint_FQN
        self._call = call

    def call_method(self, args):
        return_value = self._call(*args)
        if return_value is None:
            return return_value
        else:
            return self._return(return_value)

    def get_endpoint_FQN(self):
        return self._endpoint_FQN

    def _return(self, *args):
        return args


class RemoteSession(object):
    '''
    A context object for a Jabber-RPC session.
    '''


    def __init__(self, client, session_close_callback):
        '''
        Initializes a new RPC session.

        Arguments:
            client -- The SleekXMPP client associated with this session.
            session_close_callback -- A callback called when the
                session is closed.
        '''
        self._client = client
        self._session_close_callback = session_close_callback
        self._event = threading.Event()
        self._entries = {}
        self._callbacks = {}
        self._acls = {}
        self._lock = RLock()

    def _wait(self):
        self._event.wait()

    def _notify(self, event):
        log.debug("RPC Session as %s started.", self._client.boundjid.full)
        self._client.sendPresence()
        self._event.set()
        pass

    def _register_call(self, endpoint, method, name=None):
        '''
        Registers a method from an endpoint as remotely callable.
        '''
        if name is None:
            name = method.__name__
        key = "%s.%s" % (endpoint, name)
        log.debug("Registering call handler for %s (%s).", key, method)
        with self._lock:
            if key in self._entries:
                raise KeyError("A handler for %s has already been regisered!" % endpoint)
            self._entries[key] = JabberRPCEntry(endpoint, method)
        return key

    def _register_acl(self, endpoint, acl):
        log.debug("Registering ACL %s for endpoint %s.", repr(acl), endpoint)
        with self._lock:
            self._acls[endpoint] = acl

    def _register_callback(self, pid, callback):
        with self._lock:
            self._callbacks[pid] = callback

    def forget_callback(self, callback):
        with self._lock:
            pid = self._find_key(self._callbacks, callback)
            if pid is not None:
                del self._callback[pid]
            else:
                raise ValueError("Unknown callback!")
        pass

    def _find_key(self, dict, value):
        """return the key of dictionary dic given the value"""
        search = [k for k, v in dict.iteritems() if v == value]
        if len(search) == 0:
            return None
        else:
            return search[0]

    def _unregister_call(self, key):
        #removes the registered call
        with self._lock:
            if self._entries[key]:
                del self._entries[key]
            else:
                raise ValueError()

    def new_proxy(self, target_jid, endpoint_cls):
        '''
        Instantiates a new proxy object, which proxies to a remote
        endpoint. This method uses a class reference without
        constructor arguments to instantiate the proxy.

        Arguments:
            target_jid -- the XMPP entity ID hosting the endpoint.
            endpoint_cls -- The remote (duck) type.
        '''
        try:
            argspec = inspect.getargspec(endpoint_cls.__init__)
            args = [None] * (len(argspec[0]) - 1)
            result = endpoint_cls(*args)
            Endpoint.__init__(result, self, target_jid)
            return Proxy(result)
        except:
            traceback.print_exc(file=sys.stdout)

    def new_handler(self, acl, handler_cls, *args, **kwargs):
        '''
        Instantiates a new handler object, which is called remotely
        by others. The user can control the effect of the call by
        implementing the remote method in the local endpoint class. The
        returned reference can be called locally and will behave as a
        regular instance.

        Arguments:
            acl -- Access control list (see ACL class)
            handler_clss -- The local (duck) type.
            *args -- Constructor arguments for the local type.
            **kwargs -- Constructor keyworded arguments for the local
                type.
        '''
        argspec = inspect.getargspec(handler_cls.__init__)
        base_argspec = inspect.getargspec(Endpoint.__init__)
        if(argspec == base_argspec):
            result = handler_cls(self, self._client.boundjid.full)
        else:
            result = handler_cls(*args, **kwargs)
            Endpoint.__init__(result, self, self._client.boundjid.full)
        method_dict = result.get_methods()
        for method_name, method in method_dict.iteritems():
            #!!! self._client.plugin['xep_0009'].register_call(result.FQN(), method, method_name)
            self._register_call(result.FQN(), method, method_name)
        self._register_acl(result.FQN(), acl)
        return result

#    def is_available(self, targetCls, pto):
#        return self._client.is_available(pto)

    def _call_remote(self, pto, pmethod, callback, *arguments):
        iq = self._client.plugin['xep_0009'].make_iq_method_call(pto, pmethod, py2xml(*arguments))
        pid = iq['id']
        if callback is None:
            future = Future()
            self._register_callback(pid, future)
            iq.send()
            return future.get_value(30)
        else:
            log.debug("[RemoteSession] _call_remote %s", callback)
            self._register_callback(pid, callback)
            iq.send()

    def close(self):
        '''
        Closes this session.
        '''
        self._client.disconnect(False)
        self._session_close_callback()

    def _on_jabber_rpc_method_call(self, iq):
        iq.enable('rpc_query')
        params = iq['rpc_query']['method_call']['params']
        args = xml2py(params)
        pmethod = iq['rpc_query']['method_call']['method_name']
        try:
            with self._lock:
                entry = self._entries[pmethod]
                rules = self._acls[entry.get_endpoint_FQN()]
            if ACL.check(rules, iq['from'], pmethod):
                return_value = entry.call_method(args)
            else:
                raise AuthorizationException("Unauthorized access to %s from %s!" % (pmethod, iq['from']))
            if return_value is None:
                return_value = ()
            response = self._client.plugin['xep_0009'].make_iq_method_response(iq['id'], iq['from'], py2xml(*return_value))
            response.send()
        except InvocationException as ie:
            fault = dict()
            fault['code'] = 500
            fault['string'] = ie.get_message()
            self._client.plugin['xep_0009']._send_fault(iq, fault2xml(fault))
        except AuthorizationException as ae:
            log.error(ae.get_message())
            error = self._client.plugin['xep_0009']._forbidden(iq)
            error.send()
        except Exception as e:
            if isinstance(e, KeyError):
                log.error("No handler available for %s!", pmethod)
                error = self._client.plugin['xep_0009']._item_not_found(iq)
            else:
                traceback.print_exc(file=sys.stderr)
                log.error("An unexpected problem occurred invoking method %s!", pmethod)
                error = self._client.plugin['xep_0009']._undefined_condition(iq)
            #! print "[REMOTE.PY] _handle_remote_procedure_call AN ERROR SHOULD BE SENT NOW %s " % e
            error.send()

    def _on_jabber_rpc_method_response(self, iq):
        iq.enable('rpc_query')
        args = xml2py(iq['rpc_query']['method_response']['params'])
        pid = iq['id']
        with self._lock:
            callback = self._callbacks[pid]
            del self._callbacks[pid]
        if(len(args) > 0):
            callback.set_value(args[0])
        else:
            callback.set_value(None)
        pass

    def _on_jabber_rpc_method_response2(self, iq):
        iq.enable('rpc_query')
        if iq['rpc_query']['method_response']['fault'] is not None:
            self._on_jabber_rpc_method_fault(iq)
        else:
            args = xml2py(iq['rpc_query']['method_response']['params'])
            pid = iq['id']
            with self._lock:
                callback = self._callbacks[pid]
                del self._callbacks[pid]
            if(len(args) > 0):
                callback.set_value(args[0])
            else:
                callback.set_value(None)
            pass

    def _on_jabber_rpc_method_fault(self, iq):
        iq.enable('rpc_query')
        fault = xml2fault(iq['rpc_query']['method_response']['fault'])
        pid = iq['id']
        with self._lock:
            callback = self._callbacks[pid]
            del self._callbacks[pid]
        e = {
             500: InvocationException
        }[fault['code']](fault['string'])
        callback.cancel_with_error(e)

    def _on_jabber_rpc_error(self, iq):
        pid = iq['id']
        pmethod = self._client.plugin['xep_0009']._extract_method(iq['rpc_query'])
        code = iq['error']['code']
        type = iq['error']['type']
        condition = iq['error']['condition']
        #! print("['REMOTE.PY']._BINDING_handle_remote_procedure_error -> ERROR! ERROR! ERROR! Condition is '%s'" % condition)
        with self._lock:
            callback = self._callbacks[pid]
            del self._callbacks[pid]
        e = {
            'item-not-found': RemoteException("No remote handler available for %s at %s!" % (pmethod, iq['from'])),
            'forbidden': AuthorizationException("Forbidden to invoke remote handler for %s at %s!" % (pmethod, iq['from'])),
            'undefined-condition': RemoteException("An unexpected problem occured trying to invoke %s at %s!" % (pmethod, iq['from'])),
        }[condition]
        if e is None:
            RemoteException("An unexpected exception occurred at %s!" % iq['from'])
        callback.cancel_with_error(e)


class Remote(object):
    '''
    Bootstrap class for Jabber-RPC sessions. New sessions are openend
    with an existing XMPP client, or one is instantiated on demand.
    '''
    _instance = None
    _sessions = dict()
    _lock = threading.RLock()

    @classmethod
    def new_session_with_client(cls, client, callback=None):
        '''
        Opens a new session with a given client.

        Arguments:
            client -- An XMPP client.
            callback -- An optional callback which can be used to track
                the starting state of the session.
        '''
        with Remote._lock:
            if(client.boundjid.bare in cls._sessions):
                raise RemoteException("There already is a session associated with these credentials!")
            else:
                cls._sessions[client.boundjid.bare] = client;
        def _session_close_callback():
            with Remote._lock:
                del cls._sessions[client.boundjid.bare]
        result = RemoteSession(client, _session_close_callback)
        client.plugin['xep_0009'].xmpp.add_event_handler('jabber_rpc_method_call', result._on_jabber_rpc_method_call, threaded=True)
        client.plugin['xep_0009'].xmpp.add_event_handler('jabber_rpc_method_response', result._on_jabber_rpc_method_response, threaded=True)
        client.plugin['xep_0009'].xmpp.add_event_handler('jabber_rpc_method_fault', result._on_jabber_rpc_method_fault, threaded=True)
        client.plugin['xep_0009'].xmpp.add_event_handler('jabber_rpc_error', result._on_jabber_rpc_error, threaded=True)
        if callback is None:
            start_event_handler = result._notify
        else:
            start_event_handler = callback
        client.add_event_handler("session_start", start_event_handler)
        if client.connect():
            client.process(threaded=True)
        else:
            raise RemoteException("Could not connect to XMPP server!")
        pass
        if callback is None:
            result._wait()
        return result

    @classmethod
    def new_session(cls, jid, password, callback=None):
        '''
        Opens a new session and instantiates a new XMPP client.

        Arguments:
            jid -- The XMPP JID for logging in.
            password -- The password for logging in.
            callback -- An optional callback which can be used to track
                the starting state of the session.
        '''
        client = sleekxmpp.ClientXMPP(jid, password)
        #? Register plug-ins.
        client.registerPlugin('xep_0004') # Data Forms
        client.registerPlugin('xep_0009') # Jabber-RPC
        client.registerPlugin('xep_0030') # Service Discovery
        client.registerPlugin('xep_0060') # PubSub
        client.registerPlugin('xep_0199') # XMPP Ping
        return cls.new_session_with_client(client, callback)

