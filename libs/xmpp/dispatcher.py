##   transports.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: dispatcher.py,v 1.42 2007/05/18 23:18:36 normanr Exp $

"""
Main xmpppy mechanism. Provides library with methods to assign different handlers
to different XMPP stanzas.
Contains one tunable attribute: DefaultTimeout (25 seconds by default). It defines time that 
Dispatcher.SendAndWaitForResponce method will wait for reply stanza before giving up.
"""

import simplexml,time,sys
from protocol import *
from client import PlugIn

DefaultTimeout=25
ID=0

class Dispatcher(PlugIn):
    """ Ancestor of PlugIn class. Handles XMPP stream, i.e. aware of stream headers.
        Can be plugged out/in to restart these headers (used for SASL f.e.). """
    def __init__(self):
        PlugIn.__init__(self)
        DBG_LINE='dispatcher'
        self.handlers={}
        self._expected={}
        self._defaultHandler=None
        self._pendingExceptions=[]
        self._eventHandler=None
        self._cycleHandlers=[]
        self._exported_methods=[self.Process,self.RegisterHandler,self.RegisterDefaultHandler,\
        self.RegisterEventHandler,self.UnregisterCycleHandler,self.RegisterCycleHandler,\
        self.RegisterHandlerOnce,self.UnregisterHandler,self.RegisterProtocol,\
        self.WaitForResponse,self.SendAndWaitForResponse,self.send,self.disconnect,\
        self.SendAndCallForResponse, ]

    def dumpHandlers(self):
        """ Return set of user-registered callbacks in it's internal format.
            Used within the library to carry user handlers set over Dispatcher replugins. """
        return self.handlers
    def restoreHandlers(self,handlers):
        """ Restores user-registered callbacks structure from dump previously obtained via dumpHandlers.
            Used within the library to carry user handlers set over Dispatcher replugins. """
        self.handlers=handlers

    def _init(self):
        """ Registers default namespaces/protocols/handlers. Used internally.  """
        self.RegisterNamespace('unknown')
        self.RegisterNamespace(NS_STREAMS)
        self.RegisterNamespace(self._owner.defaultNamespace)
        self.RegisterProtocol('iq',Iq)
        self.RegisterProtocol('presence',Presence)
        self.RegisterProtocol('message',Message)
        self.RegisterDefaultHandler(self.returnStanzaHandler)
        self.RegisterHandler('error',self.streamErrorHandler,xmlns=NS_STREAMS)

    def plugin(self, owner):
        """ Plug the Dispatcher instance into Client class instance and send initial stream header. Used internally."""
        self._init()
        for method in self._old_owners_methods:
            if method.__name__=='send': self._owner_send=method; break
        self._owner.lastErrNode=None
        self._owner.lastErr=None
        self._owner.lastErrCode=None
        self.StreamInit()

    def plugout(self):
        """ Prepares instance to be destructed. """
        self.Stream.dispatch=None
        self.Stream.DEBUG=None
        self.Stream.features=None
        self.Stream.destroy()

    def StreamInit(self):
        """ Send an initial stream header. """
        self.Stream=simplexml.NodeBuilder()
        self.Stream._dispatch_depth=2
        self.Stream.dispatch=self.dispatch
        self.Stream.stream_header_received=self._check_stream_start
        self._owner.debug_flags.append(simplexml.DBG_NODEBUILDER)
        self.Stream.DEBUG=self._owner.DEBUG
        self.Stream.features=None
        self._metastream=Node('stream:stream')
        self._metastream.setNamespace(self._owner.Namespace)
        self._metastream.setAttr('version','1.0')
        self._metastream.setAttr('xmlns:stream',NS_STREAMS)
        self._metastream.setAttr('to',self._owner.Server)
        self._owner.send("<?xml version='1.0'?>%s>"%str(self._metastream)[:-2])

    def _check_stream_start(self,ns,tag,attrs):
        if ns<>NS_STREAMS or tag<>'stream':
            raise ValueError('Incorrect stream start: (%s,%s). Terminating.'%(tag,ns))

    def Process(self, timeout=0):
        """ Check incoming stream for data waiting. If "timeout" is positive - block for as max. this time.
            Returns:
            1) length of processed data if some data were processed;
            2) '0' string if no data were processed but link is alive;
            3) 0 (zero) if underlying connection is closed.
            Take note that in case of disconnection detect during Process() call
            disconnect handlers are called automatically.
        """
        for handler in self._cycleHandlers: handler(self)
        if len(self._pendingExceptions) > 0:
            _pendingException = self._pendingExceptions.pop()
            raise _pendingException[0], _pendingException[1], _pendingException[2]
        if self._owner.Connection.pending_data(timeout):
            try: data=self._owner.Connection.receive()
            except IOError: return
            self.Stream.Parse(data)
            if len(self._pendingExceptions) > 0:
                _pendingException = self._pendingExceptions.pop()
                raise _pendingException[0], _pendingException[1], _pendingException[2]
            if data: return len(data)
        return '0'      # It means that nothing is received but link is alive.
        
    def RegisterNamespace(self,xmlns,order='info'):
        """ Creates internal structures for newly registered namespace.
            You can register handlers for this namespace afterwards. By default one namespace
            already registered (jabber:client or jabber:component:accept depending on context. """
        self.DEBUG('Registering namespace "%s"'%xmlns,order)
        self.handlers[xmlns]={}
        self.RegisterProtocol('unknown',Protocol,xmlns=xmlns)
        self.RegisterProtocol('default',Protocol,xmlns=xmlns)

    def RegisterProtocol(self,tag_name,Proto,xmlns=None,order='info'):
        """ Used to declare some top-level stanza name to dispatcher.
           Needed to start registering handlers for such stanzas.
           Iq, message and presence protocols are registered by default. """
        if not xmlns: xmlns=self._owner.defaultNamespace
        self.DEBUG('Registering protocol "%s" as %s(%s)'%(tag_name,Proto,xmlns), order)
        self.handlers[xmlns][tag_name]={type:Proto, 'default':[]}

    def RegisterNamespaceHandler(self,xmlns,handler,typ='',ns='', makefirst=0, system=0):
        """ Register handler for processing all stanzas for specified namespace. """
        self.RegisterHandler('default', handler, typ, ns, xmlns, makefirst, system)

    def RegisterHandler(self,name,handler,typ='',ns='',xmlns=None, makefirst=0, system=0):
        """Register user callback as stanzas handler of declared type. Callback must take
           (if chained, see later) arguments: dispatcher instance (for replying), incomed
           return of previous handlers.
           The callback must raise xmpp.NodeProcessed just before return if it want preven
           callbacks to be called with the same stanza as argument _and_, more importantly
           library from returning stanza to sender with error set (to be enabled in 0.2 ve
            Arguments:
              "name" - name of stanza. F.e. "iq".
              "handler" - user callback.
              "typ" - value of stanza's "type" attribute. If not specified any value match
              "ns" - namespace of child that stanza must contain.
              "chained" - chain together output of several handlers.
              "makefirst" - insert handler in the beginning of handlers list instead of
                adding it to the end. Note that more common handlers (i.e. w/o "typ" and "
                will be called first nevertheless.
              "system" - call handler even if NodeProcessed Exception were raised already.
            """
        if not xmlns: xmlns=self._owner.defaultNamespace
        self.DEBUG('Registering handler %s for "%s" type->%s ns->%s(%s)'%(handler,name,typ,ns,xmlns), 'info')
        if not typ and not ns: typ='default'
        if not self.handlers.has_key(xmlns): self.RegisterNamespace(xmlns,'warn')
        if not self.handlers[xmlns].has_key(name): self.RegisterProtocol(name,Protocol,xmlns,'warn')
        if not self.handlers[xmlns][name].has_key(typ+ns): self.handlers[xmlns][name][typ+ns]=[]
        if makefirst: self.handlers[xmlns][name][typ+ns].insert(0,{'func':handler,'system':system})
        else: self.handlers[xmlns][name][typ+ns].append({'func':handler,'system':system})

    def RegisterHandlerOnce(self,name,handler,typ='',ns='',xmlns=None,makefirst=0, system=0):
        """ Unregister handler after first call (not implemented yet). """
        if not xmlns: xmlns=self._owner.defaultNamespace
        self.RegisterHandler(name, handler, typ, ns, xmlns, makefirst, system)

    def UnregisterHandler(self,name,handler,typ='',ns='',xmlns=None):
        """ Unregister handler. "typ" and "ns" must be specified exactly the same as with registering."""
        if not xmlns: xmlns=self._owner.defaultNamespace
        if not self.handlers.has_key(xmlns): return
        if not typ and not ns: typ='default'
        for pack in self.handlers[xmlns][name][typ+ns]:
            if handler==pack['func']: break
        else: pack=None
        try: self.handlers[xmlns][name][typ+ns].remove(pack)
        except ValueError: pass

    def RegisterDefaultHandler(self,handler):
        """ Specify the handler that will be used if no NodeProcessed exception were raised.
            This is returnStanzaHandler by default. """
        self._defaultHandler=handler

    def RegisterEventHandler(self,handler):
        """ Register handler that will process events. F.e. "FILERECEIVED" event. """
        self._eventHandler=handler

    def returnStanzaHandler(self,conn,stanza):
        """ Return stanza back to the sender with <feature-not-implemennted/> error set. """
        if stanza.getType() in ['get','set']:
            conn.send(Error(stanza,ERR_FEATURE_NOT_IMPLEMENTED))

    def streamErrorHandler(self,conn,error):
        name,text='error',error.getData()
        for tag in error.getChildren():
            if tag.getNamespace()==NS_XMPP_STREAMS:
                if tag.getName()=='text': text=tag.getData()
                else: name=tag.getName()
        if name in stream_exceptions.keys(): exc=stream_exceptions[name]
        else: exc=StreamError
        raise exc((name,text))

    def RegisterCycleHandler(self,handler):
        """ Register handler that will be called on every Dispatcher.Process() call. """
        if handler not in self._cycleHandlers: self._cycleHandlers.append(handler)

    def UnregisterCycleHandler(self,handler):
        """ Unregister handler that will is called on every Dispatcher.Process() call."""
        if handler in self._cycleHandlers: self._cycleHandlers.remove(handler)

    def Event(self,realm,event,data):
        """ Raise some event. Takes three arguments:
            1) "realm" - scope of event. Usually a namespace. 
            2) "event" - the event itself. F.e. "SUCESSFULL SEND".
            3) data that comes along with event. Depends on event."""
        if self._eventHandler: self._eventHandler(realm,event,data)

    def dispatch(self,stanza,session=None,direct=0):
        """ Main procedure that performs XMPP stanza recognition and calling apppropriate handlers for it.
            Called internally. """
        if not session: session=self
        session.Stream._mini_dom=None
        name=stanza.getName()

        if not direct and self._owner._route:
            if name == 'route':
                if stanza.getAttr('error') == None:
                    if len(stanza.getChildren()) == 1:
                        stanza = stanza.getChildren()[0]
                        name=stanza.getName()
                    else:
                        for each in stanza.getChildren():
                            self.dispatch(each,session,direct=1)
                        return
            elif name == 'presence':
                return
            elif name in ('features','bind'):
                pass
            else:
                raise UnsupportedStanzaType(name)

        if name=='features': session.Stream.features=stanza

        xmlns=stanza.getNamespace()
        if not self.handlers.has_key(xmlns):
            self.DEBUG("Unknown namespace: " + xmlns,'warn')
            xmlns='unknown'
        if not self.handlers[xmlns].has_key(name):
            self.DEBUG("Unknown stanza: " + name,'warn')
            name='unknown'
        else:
            self.DEBUG("Got %s/%s stanza"%(xmlns,name), 'ok')

        if stanza.__class__.__name__=='Node': stanza=self.handlers[xmlns][name][type](node=stanza)

        typ=stanza.getType()
        if not typ: typ=''
        stanza.props=stanza.getProperties()
        ID=stanza.getID()

        session.DEBUG("Dispatching %s stanza with type->%s props->%s id->%s"%(name,typ,stanza.props,ID),'ok')

        list=['default']                                                     # we will use all handlers:
        if self.handlers[xmlns][name].has_key(typ): list.append(typ)                # from very common...
        for prop in stanza.props:
            if self.handlers[xmlns][name].has_key(prop): list.append(prop)
            if typ and self.handlers[xmlns][name].has_key(typ+prop): list.append(typ+prop)  # ...to very particular

        chain=self.handlers[xmlns]['default']['default']
        for key in list:
            if key: chain = chain + self.handlers[xmlns][name][key]

        output=''
        if session._expected.has_key(ID):
            user=0
            if type(session._expected[ID])==type(()):
                cb,args=session._expected[ID]
                session.DEBUG("Expected stanza arrived. Callback %s(%s) found!"%(cb,args),'ok')
                try: cb(session,stanza,**args)
                except Exception, typ:
                    if typ.__class__.__name__<>'NodeProcessed': raise
            else:
                session.DEBUG("Expected stanza arrived!",'ok')
                session._expected[ID]=stanza
        else: user=1
        for handler in chain:
            if user or handler['system']:
                try:
                    handler['func'](session,stanza)
                except Exception, typ:
                    if typ.__class__.__name__<>'NodeProcessed':
                        self._pendingExceptions.insert(0, sys.exc_info())
                        return
                    user=0
        if user and self._defaultHandler: self._defaultHandler(session,stanza)

    def WaitForResponse(self, ID, timeout=DefaultTimeout):
        """ Block and wait until stanza with specific "id" attribute will come.
            If no such stanza is arrived within timeout, return None.
            If operation failed for some reason then owner's attributes
            lastErrNode, lastErr and lastErrCode are set accordingly. """
        self._expected[ID]=None
        has_timed_out=0
        abort_time=time.time() + timeout
        self.DEBUG("Waiting for ID:%s with timeout %s..." % (ID,timeout),'wait')
        while not self._expected[ID]:
            if not self.Process(0.04):
                self._owner.lastErr="Disconnect"
                return None
            if time.time() > abort_time:
                self._owner.lastErr="Timeout"
                return None
        response=self._expected[ID]
        del self._expected[ID]
        if response.getErrorCode():
            self._owner.lastErrNode=response
            self._owner.lastErr=response.getError()
            self._owner.lastErrCode=response.getErrorCode()
        return response

    def SendAndWaitForResponse(self, stanza, timeout=DefaultTimeout):
        """ Put stanza on the wire and wait for recipient's response to it. """
        return self.WaitForResponse(self.send(stanza),timeout)

    def SendAndCallForResponse(self, stanza, func, args={}):
        """ Put stanza on the wire and call back when recipient replies.
            Additional callback arguments can be specified in args. """
        self._expected[self.send(stanza)]=(func,args)

    def send(self,stanza):
        """ Serialise stanza and put it on the wire. Assign an unique ID to it before send.
            Returns assigned ID."""
        if type(stanza) in [type(''), type(u'')]: return self._owner_send(stanza)
        if not isinstance(stanza,Protocol): _ID=None
        elif not stanza.getID():
            global ID
            ID+=1
            _ID=`ID`
            stanza.setID(_ID)
        else: _ID=stanza.getID()
        if self._owner._registered_name and not stanza.getAttr('from'): stanza.setAttr('from',self._owner._registered_name)
        if self._owner._route and stanza.getName()!='bind':
            to=self._owner.Server
            if stanza.getTo() and stanza.getTo().getDomain():
                to=stanza.getTo().getDomain()
            frm=stanza.getFrom()
            if frm.getDomain():
                frm=frm.getDomain()
            route=Protocol('route',to=to,frm=frm,payload=[stanza])
            stanza=route
        stanza.setNamespace(self._owner.Namespace)
        stanza.setParent(self._metastream)
        self._owner_send(stanza)
        return _ID

    def disconnect(self):
        """ Send a stream terminator and and handle all incoming stanzas before stream closure. """
        self._owner_send('</stream:stream>')
        while self.Process(1): pass
