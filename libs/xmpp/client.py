##   client.py
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

# $Id: client.py,v 1.61 2009/04/07 06:19:42 snakeru Exp $

"""
Provides PlugIn class functionality to develop extentions for xmpppy.
Also provides Client and Component classes implementations as the
examples of xmpppy structures usage.
These classes can be used for simple applications "AS IS" though.
"""

import socket
import debug
Debug=debug
Debug.DEBUGGING_IS_ON=1
Debug.Debug.colors['socket']=debug.color_dark_gray
Debug.Debug.colors['CONNECTproxy']=debug.color_dark_gray
Debug.Debug.colors['nodebuilder']=debug.color_brown
Debug.Debug.colors['client']=debug.color_cyan
Debug.Debug.colors['component']=debug.color_cyan
Debug.Debug.colors['dispatcher']=debug.color_green
Debug.Debug.colors['browser']=debug.color_blue
Debug.Debug.colors['auth']=debug.color_yellow
Debug.Debug.colors['roster']=debug.color_magenta
Debug.Debug.colors['ibb']=debug.color_yellow

Debug.Debug.colors['down']=debug.color_brown
Debug.Debug.colors['up']=debug.color_brown
Debug.Debug.colors['data']=debug.color_brown
Debug.Debug.colors['ok']=debug.color_green
Debug.Debug.colors['warn']=debug.color_yellow
Debug.Debug.colors['error']=debug.color_red
Debug.Debug.colors['start']=debug.color_dark_gray
Debug.Debug.colors['stop']=debug.color_dark_gray
Debug.Debug.colors['sent']=debug.color_yellow
Debug.Debug.colors['got']=debug.color_bright_cyan

DBG_CLIENT='client'
DBG_COMPONENT='component'

class PlugIn:
    """ Common xmpppy plugins infrastructure: plugging in/out, debugging. """
    def __init__(self):
        self._exported_methods=[]
        self.DBG_LINE=self.__class__.__name__.lower()

    def PlugIn(self,owner):
        """ Attach to main instance and register ourself and all our staff in it. """
        self._owner=owner
        if self.DBG_LINE not in owner.debug_flags:
            owner.debug_flags.append(self.DBG_LINE)
        self.DEBUG('Plugging %s into %s'%(self,self._owner),'start')
        if owner.__dict__.has_key(self.__class__.__name__):
            return self.DEBUG('Plugging ignored: another instance already plugged.','error')
        self._old_owners_methods=[]
        for method in self._exported_methods:
            if owner.__dict__.has_key(method.__name__):
                self._old_owners_methods.append(owner.__dict__[method.__name__])
            owner.__dict__[method.__name__]=method
        owner.__dict__[self.__class__.__name__]=self
        if self.__class__.__dict__.has_key('plugin'): return self.plugin(owner)
 
    def PlugOut(self):
        """ Unregister all our staff from main instance and detach from it. """
        self.DEBUG('Plugging %s out of %s.'%(self,self._owner),'stop')
        ret = None
        if self.__class__.__dict__.has_key('plugout'): ret = self.plugout()
        self._owner.debug_flags.remove(self.DBG_LINE)
        for method in self._exported_methods: del self._owner.__dict__[method.__name__]
        for method in self._old_owners_methods: self._owner.__dict__[method.__name__]=method
        del self._owner.__dict__[self.__class__.__name__]
        return ret

    def DEBUG(self,text,severity='info'):
        """ Feed a provided debug line to main instance's debug facility along with our ID string. """
        self._owner.DEBUG(self.DBG_LINE,text,severity)

import transports,dispatcher,auth,roster
class CommonClient:
    """ Base for Client and Component classes."""
    def __init__(self,server,port=5222,debug=['always', 'nodebuilder']):
        """ Caches server name and (optionally) port to connect to. "debug" parameter specifies
            the debug IDs that will go into debug output. You can either specifiy an "include"
            or "exclude" list. The latter is done via adding "always" pseudo-ID to the list.
            Full list: ['nodebuilder', 'dispatcher', 'gen_auth', 'SASL_auth', 'bind', 'socket', 
             'CONNECTproxy', 'TLS', 'roster', 'browser', 'ibb'] . """
        if self.__class__.__name__=='Client': self.Namespace,self.DBG='jabber:client',DBG_CLIENT
        elif self.__class__.__name__=='Component': self.Namespace,self.DBG=dispatcher.NS_COMPONENT_ACCEPT,DBG_COMPONENT
        self.defaultNamespace=self.Namespace
        self.disconnect_handlers=[]
        self.Server=server
        self.Port=port
        if debug and type(debug)<>list: debug=['always', 'nodebuilder']
        self._DEBUG=Debug.Debug(debug)
        self.DEBUG=self._DEBUG.Show
        self.debug_flags=self._DEBUG.debug_flags
        self.debug_flags.append(self.DBG)
        self._owner=self
        self._registered_name=None
        self.RegisterDisconnectHandler(self.DisconnectHandler)
        self.connected=''
        self._route=0

    def RegisterDisconnectHandler(self,handler):
        """ Register handler that will be called on disconnect."""
        self.disconnect_handlers.append(handler)

    def UnregisterDisconnectHandler(self,handler):
        """ Unregister handler that is called on disconnect."""
        self.disconnect_handlers.remove(handler)

    def disconnected(self):
        """ Called on disconnection. Calls disconnect handlers and cleans things up. """
        self.connected=''
        self.DEBUG(self.DBG,'Disconnect detected','stop')
        self.disconnect_handlers.reverse()
        for i in self.disconnect_handlers: i()
        self.disconnect_handlers.reverse()
        if self.__dict__.has_key('TLS'): self.TLS.PlugOut()

    def DisconnectHandler(self):
        """ Default disconnect handler. Just raises an IOError.
            If you choosed to use this class in your production client,
            override this method or at least unregister it. """
        raise IOError('Disconnected from server.')

    def event(self,eventName,args={}):
        """ Default event handler. To be overriden. """
        print "Event: ",(eventName,args)

    def isConnected(self):
        """ Returns connection state. F.e.: None / 'tls' / 'tcp+non_sasl' . """
        return self.connected

    def reconnectAndReauth(self):
        """ Example of reconnection method. In fact, it can be used to batch connection and auth as well. """
        handlerssave=self.Dispatcher.dumpHandlers()
        if self.__dict__.has_key('ComponentBind'): self.ComponentBind.PlugOut()
        if self.__dict__.has_key('Bind'): self.Bind.PlugOut()
        self._route=0
        if self.__dict__.has_key('NonSASL'): self.NonSASL.PlugOut()
        if self.__dict__.has_key('SASL'): self.SASL.PlugOut()
        if self.__dict__.has_key('TLS'): self.TLS.PlugOut()
        self.Dispatcher.PlugOut()
        if self.__dict__.has_key('HTTPPROXYsocket'): self.HTTPPROXYsocket.PlugOut()
        if self.__dict__.has_key('TCPsocket'): self.TCPsocket.PlugOut()
        if not self.connect(server=self._Server,proxy=self._Proxy): return
        if not self.auth(self._User,self._Password,self._Resource): return
        self.Dispatcher.restoreHandlers(handlerssave)
        return self.connected

    def connect(self,server=None,proxy=None,ssl=None,use_srv=None):
        """ Make a tcp/ip connection, protect it with tls/ssl if possible and start XMPP stream.
            Returns None or 'tcp' or 'tls', depending on the result."""
        if not server: server=(self.Server,self.Port)
        if proxy: sock=transports.HTTPPROXYsocket(proxy,server,use_srv)
        else: sock=transports.TCPsocket(server,use_srv)
        connected=sock.PlugIn(self)
        if not connected: 
            sock.PlugOut()
            return
        self._Server,self._Proxy=server,proxy
        self.connected='tcp'
        if (ssl is None and self.Connection.getPort() in (5223, 443)) or ssl:
            try:               # FIXME. This should be done in transports.py
                transports.TLS().PlugIn(self,now=1)
                self.connected='ssl'
            except socket.sslerror:
                return
        dispatcher.Dispatcher().PlugIn(self)
        while self.Dispatcher.Stream._document_attrs is None:
            if not self.Process(1): return
        if self.Dispatcher.Stream._document_attrs.has_key('version') and self.Dispatcher.Stream._document_attrs['version']=='1.0':
            while not self.Dispatcher.Stream.features and self.Process(1): pass      # If we get version 1.0 stream the features tag MUST BE presented
        return self.connected

class Client(CommonClient):
    """ Example client class, based on CommonClient. """
    def connect(self,server=None,proxy=None,secure=None,use_srv=True):
        """ Connect to jabber server. If you want to specify different ip/port to connect to you can
            pass it as tuple as first parameter. If there is HTTP proxy between you and server 
            specify it's address and credentials (if needed) in the second argument.
            If you want ssl/tls support to be discovered and enable automatically - leave third argument as None. (ssl will be autodetected only if port is 5223 or 443)
            If you want to force SSL start (i.e. if port 5223 or 443 is remapped to some non-standard port) then set it to 1.
            If you want to disable tls/ssl support completely, set it to 0.
            Example: connect(('192.168.5.5',5222),{'host':'proxy.my.net','port':8080,'user':'me','password':'secret'})
            Returns '' or 'tcp' or 'tls', depending on the result."""
        if not CommonClient.connect(self,server,proxy,secure,use_srv) or secure<>None and not secure: return self.connected
        transports.TLS().PlugIn(self)
        if not self.Dispatcher.Stream._document_attrs.has_key('version') or not self.Dispatcher.Stream._document_attrs['version']=='1.0': return self.connected
        while not self.Dispatcher.Stream.features and self.Process(1): pass      # If we get version 1.0 stream the features tag MUST BE presented
        if not self.Dispatcher.Stream.features.getTag('starttls'): return self.connected       # TLS not supported by server
        while not self.TLS.starttls and self.Process(1): pass
        if not hasattr(self, 'TLS') or self.TLS.starttls!='success': self.event('tls_failed'); return self.connected
        self.connected='tls'
        return self.connected

    def auth(self,user,password,resource='',sasl=1):
        """ Authenticate connnection and bind resource. If resource is not provided
            random one or library name used. """
        self._User,self._Password,self._Resource=user,password,resource
        while not self.Dispatcher.Stream._document_attrs and self.Process(1): pass
        if self.Dispatcher.Stream._document_attrs.has_key('version') and self.Dispatcher.Stream._document_attrs['version']=='1.0':
            while not self.Dispatcher.Stream.features and self.Process(1): pass      # If we get version 1.0 stream the features tag MUST BE presented
        if sasl: auth.SASL(user,password).PlugIn(self)
        if not sasl or self.SASL.startsasl=='not-supported':
            if not resource: resource='xmpppy'
            if auth.NonSASL(user,password,resource).PlugIn(self):
                self.connected+='+old_auth'
                return 'old_auth'
            return
        self.SASL.auth()
        while self.SASL.startsasl=='in-process' and self.Process(1): pass
        if self.SASL.startsasl=='success':
            auth.Bind().PlugIn(self)
            while self.Bind.bound is None and self.Process(1): pass
            if self.Bind.Bind(resource):
                self.connected+='+sasl'
                return 'sasl'
        else:
            if self.__dict__.has_key('SASL'): self.SASL.PlugOut()

    def getRoster(self):
        """ Return the Roster instance, previously plugging it in and
            requesting roster from server if needed. """
        if not self.__dict__.has_key('Roster'): roster.Roster().PlugIn(self)
        return self.Roster.getRoster()

    def sendInitPresence(self,requestRoster=1):
        """ Send roster request and initial <presence/>.
            You can disable the first by setting requestRoster argument to 0. """
        self.sendPresence(requestRoster=requestRoster)

    def sendPresence(self,jid=None,typ=None,requestRoster=0):
        """ Send some specific presence state.
            Can also request roster from server if according agrument is set."""
        if requestRoster: roster.Roster().PlugIn(self)
        self.send(dispatcher.Presence(to=jid, typ=typ))

class Component(CommonClient):
    """ Component class. The only difference from CommonClient is ability to perform component authentication. """
    def __init__(self,transport,port=5347,typ=None,debug=['always', 'nodebuilder'],domains=None,sasl=0,bind=0,route=0,xcp=0):
        """ Init function for Components.
            As components use a different auth mechanism which includes the namespace of the component.
            Jabberd1.4 and Ejabberd use the default namespace then for all client messages.
            Jabberd2 uses jabber:client.
            'transport' argument is a transport name that you are going to serve (f.e. "irc.localhost").
            'port' can be specified if 'transport' resolves to correct IP. If it is not then you'll have to specify IP
            and port while calling "connect()".
            If you are going to serve several different domains with single Component instance - you must list them ALL
            in the 'domains' argument.
            For jabberd2 servers you should set typ='jabberd2' argument.
        """
        CommonClient.__init__(self,transport,port=port,debug=debug)
        self.typ=typ
        self.sasl=sasl
        self.bind=bind
        self.route=route
        self.xcp=xcp
        if domains:
            self.domains=domains
        else:
            self.domains=[transport]
    
    def connect(self,server=None,proxy=None):
        """ This will connect to the server, and if the features tag is found then set
            the namespace to be jabber:client as that is required for jabberd2.
            'server' and 'proxy' arguments have the same meaning as in xmpp.Client.connect() """
        if self.sasl:
            self.Namespace=auth.NS_COMPONENT_1
            self.Server=server[0]
        CommonClient.connect(self,server=server,proxy=proxy)
        if self.connected and (self.typ=='jabberd2' or not self.typ and self.Dispatcher.Stream.features != None) and (not self.xcp):
            self.defaultNamespace=auth.NS_CLIENT
            self.Dispatcher.RegisterNamespace(self.defaultNamespace)
            self.Dispatcher.RegisterProtocol('iq',dispatcher.Iq)
            self.Dispatcher.RegisterProtocol('message',dispatcher.Message)
            self.Dispatcher.RegisterProtocol('presence',dispatcher.Presence)
        return self.connected

    def dobind(self, sasl):
        # This has to be done before binding, because we can receive a route stanza before binding finishes
        self._route = self.route
        if self.bind:
            for domain in self.domains:
                auth.ComponentBind(sasl).PlugIn(self)
                while self.ComponentBind.bound is None: self.Process(1)
                if (not self.ComponentBind.Bind(domain)):
                    self.ComponentBind.PlugOut()
                    return
                self.ComponentBind.PlugOut()

    def auth(self,name,password,dup=None):
        """ Authenticate component "name" with password "password"."""
        self._User,self._Password,self._Resource=name,password,''
        try:
            if self.sasl: auth.SASL(name,password).PlugIn(self)
            if not self.sasl or self.SASL.startsasl=='not-supported':
                if auth.NonSASL(name,password,'').PlugIn(self):
                    self.dobind(sasl=False)
                    self.connected+='+old_auth'
                    return 'old_auth'
                return
            self.SASL.auth()
            while self.SASL.startsasl=='in-process' and self.Process(1): pass
            if self.SASL.startsasl=='success':
                self.dobind(sasl=True)
                self.connected+='+sasl'
                return 'sasl'
            else:
                raise auth.NotAuthorized(self.SASL.startsasl)
        except:
            self.DEBUG(self.DBG,"Failed to authenticate %s"%name,'error')
