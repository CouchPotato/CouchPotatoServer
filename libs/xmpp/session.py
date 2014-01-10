##
##   XMPP server
##
##   Copyright (C) 2004 Alexey "Snake" Nezhdanov
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

__version__="$Id"

"""
When your handler is called it is getting the session instance as the first argument.
This is the difference from xmpppy 0.1 where you got the "Client" instance.
With Session class you can have "multi-session" client instead of having
one client for each connection. Is is specifically important when you are
writing the server.
"""

from protocol import *

# Transport-level flags
SOCKET_UNCONNECTED  =0
SOCKET_ALIVE        =1
SOCKET_DEAD         =2
# XML-level flags
STREAM__NOT_OPENED =1
STREAM__OPENED     =2
STREAM__CLOSING    =3
STREAM__CLOSED     =4
# XMPP-session flags
SESSION_NOT_AUTHED =1
SESSION_AUTHED     =2
SESSION_BOUND      =3
SESSION_OPENED     =4
SESSION_CLOSED     =5

class Session:
    """
    The Session class instance is used for storing all session-related info like 
    credentials, socket/xml stream/session state flags, roster items (in case of
    client type connection) etc.
    Session object have no means of discovering is any info is ready to be read.
    Instead you should use poll() (recomended) or select() methods for this purpose.
    Session can be one of two types: 'server' and 'client'. 'server' session handles
    inbound connection and 'client' one used to create an outbound one.
    Session instance have multitude of internal attributes. The most imporant is the 'peer' one.
    It is set once the peer is authenticated (client).
    """
    def __init__(self,socket,owner,xmlns=None,peer=None):
        """ When the session is created it's type (client/server) is determined from the beginning.
            socket argument is the pre-created socket-like object.
            It must have the following methods: send, recv, fileno, close.
            owner is the 'master' instance that have Dispatcher plugged into it and generally
            will take care about all session events.
            xmlns is the stream namespace that will be used. Client must set this argument
            If server sets this argument than stream will be dropped if opened with some another namespace.
            peer is the name of peer instance. This is the flag that differentiates client session from
            server session. Client must set it to the name of the server that will be connected, server must
            leave this argument alone.
            """
        self.xmlns=xmlns
        if peer:
            self.TYP='client'
            self.peer=peer
            self._socket_state=SOCKET_UNCONNECTED
        else:
            self.TYP='server'
            self.peer=None
            self._socket_state=SOCKET_ALIVE
        self._sock=socket
        self._send=socket.send
        self._recv=socket.recv
        self.fileno=socket.fileno
        self._registered=0

        self.Dispatcher=owner.Dispatcher
        self.DBG_LINE='session'
        self.DEBUG=owner.Dispatcher.DEBUG
        self._expected={}
        self._owner=owner
        if self.TYP=='server': self.ID=`random.random()`[2:]
        else: self.ID=None

        self.sendbuffer=''
        self._stream_pos_queued=None
        self._stream_pos_sent=0
        self.deliver_key_queue=[]
        self.deliver_queue_map={}
        self.stanza_queue=[]

        self._session_state=SESSION_NOT_AUTHED
        self.waiting_features=[]
        for feature in [NS_TLS,NS_SASL,NS_BIND,NS_SESSION]:
            if feature in owner.features: self.waiting_features.append(feature)
        self.features=[]
        self.feature_in_process=None
        self.slave_session=None
        self.StartStream()

    def StartStream(self):
        """ This method is used to initialise the internal xml expat parser
            and to send initial stream header (in case of client connection).
            Should be used after initial connection and after every stream restart."""
        self._stream_state=STREAM__NOT_OPENED
        self.Stream=simplexml.NodeBuilder()
        self.Stream._dispatch_depth=2
        self.Stream.dispatch=self._dispatch
        self.Parse=self.Stream.Parse
        self.Stream.stream_footer_received=self._stream_close
        if self.TYP=='client':
            self.Stream.stream_header_received=self._catch_stream_id
            self._stream_open()
        else:
            self.Stream.stream_header_received=self._stream_open

    def receive(self):
        """ Reads all pending incoming data.
            Raises IOError on disconnection.
            Blocks until at least one byte is read."""
        try: received = self._recv(10240)
        except: received = ''

        if len(received): # length of 0 means disconnect
            self.DEBUG(`self.fileno()`+' '+received,'got')
        else:
            self.DEBUG('Socket error while receiving data','error')
            self.set_socket_state(SOCKET_DEAD)
            raise IOError("Peer disconnected")
        return received

    def sendnow(self,chunk):
        """ Put chunk into "immidiatedly send" queue.
            Should only be used for auth/TLS stuff and like.
            If you just want to shedule regular stanza for delivery use enqueue method.
        """
        if isinstance(chunk,Node): chunk = chunk.__str__().encode('utf-8')
        elif type(chunk)==type(u''): chunk = chunk.encode('utf-8')
        self.enqueue(chunk)

    def enqueue(self,stanza):
        """ Takes Protocol instance as argument.
            Puts stanza into "send" fifo queue. Items into the send queue are hold until
            stream authenticated. After that this method is effectively the same as "sendnow" method."""
        if isinstance(stanza,Protocol):
            self.stanza_queue.append(stanza)
        else: self.sendbuffer+=stanza
        if self._socket_state>=SOCKET_ALIVE: self.push_queue()

    def push_queue(self,failreason=ERR_RECIPIENT_UNAVAILABLE):
        """ If stream is authenticated than move items from "send" queue to "immidiatedly send" queue.
            Else if the stream is failed then return all queued stanzas with error passed as argument.
            Otherwise do nothing."""
        # If the stream authed - convert stanza_queue into sendbuffer and set the checkpoints

        if self._stream_state>=STREAM__CLOSED or self._socket_state>=SOCKET_DEAD: # the stream failed. Return all stanzas that are still waiting for delivery.
            self._owner.deactivatesession(self)
            for key in self.deliver_key_queue:                                          # Not sure. May be I
                self._dispatch(Error(self.deliver_queue_map[key],failreason),trusted=1) # should simply re-dispatch it?
            for stanza in self.stanza_queue:                                            # But such action can invoke
                self._dispatch(Error(stanza,failreason),trusted=1)                      # Infinite loops in case of S2S connection...
            self.deliver_queue_map,self.deliver_key_queue,self.stanza_queue={},[],[]
            return
        elif self._session_state>=SESSION_AUTHED:       # FIXME! Должен быть какой-то другой флаг.
            #### LOCK_QUEUE
            for stanza in self.stanza_queue:
                txt=stanza.__str__().encode('utf-8')
                self.sendbuffer+=txt
                self._stream_pos_queued+=len(txt)       # should be re-evaluated for SSL connection.
                self.deliver_queue_map[self._stream_pos_queued]=stanza     # position of the stream when stanza will be successfully and fully sent
                self.deliver_key_queue.append(self._stream_pos_queued)
            self.stanza_queue=[]
            #### UNLOCK_QUEUE

    def flush_queue(self):
        """ Put the "immidiatedly send" queue content on the wire. Blocks until at least one byte sent."""
        if self.sendbuffer:
            try:
                # LOCK_QUEUE
                sent=self._send(self.sendbuffer)    # Блокирующая штучка!
            except:
                # UNLOCK_QUEUE
                self.set_socket_state(SOCKET_DEAD)
                self.DEBUG("Socket error while sending data",'error')
                return self.terminate_stream()
            self.DEBUG(`self.fileno()`+' '+self.sendbuffer[:sent],'sent')
            self._stream_pos_sent+=sent
            self.sendbuffer=self.sendbuffer[sent:]
            self._stream_pos_delivered=self._stream_pos_sent            # Should be acquired from socket somehow. Take SSL into account.
            while self.deliver_key_queue and self._stream_pos_delivered>self.deliver_key_queue[0]:
                del self.deliver_queue_map[self.deliver_key_queue[0]]
                self.deliver_key_queue.remove(self.deliver_key_queue[0])
            # UNLOCK_QUEUE

    def _dispatch(self,stanza,trusted=0):
        """ This is callback that is used to pass the received stanza forth to owner's dispatcher
            _if_ the stream is authorised. Otherwise the stanza is just dropped.
            The 'trusted' argument is used to emulate stanza receive.
            This method is used internally.
        """
        self._owner.packets+=1
        if self._stream_state==STREAM__OPENED or trusted:               # if the server really should reject all stanzas after he is closed stream (himeself)?
            self.DEBUG(stanza.__str__(),'dispatch')
            stanza.trusted=trusted
            return self.Dispatcher.dispatch(stanza,self)

    def _catch_stream_id(self,ns=None,tag='stream',attrs={}):
        """ This callback is used to detect the stream namespace of incoming stream. Used internally. """
        if not attrs.has_key('id') or not attrs['id']:
            return self.terminate_stream(STREAM_INVALID_XML)
        self.ID=attrs['id']
        if not attrs.has_key('version'): self._owner.Dialback(self)

    def _stream_open(self,ns=None,tag='stream',attrs={}):
        """ This callback is used to handle opening stream tag of the incoming stream.
            In the case of client session it just make some validation.
            Server session also sends server headers and if the stream valid the features node.
            Used internally. """
        text='<?xml version="1.0" encoding="utf-8"?>\n<stream:stream'
        if self.TYP=='client':
            text+=' to="%s"'%self.peer
        else:
            text+=' id="%s"'%self.ID
            if not attrs.has_key('to'): text+=' from="%s"'%self._owner.servernames[0]
            else: text+=' from="%s"'%attrs['to']
        if attrs.has_key('xml:lang'): text+=' xml:lang="%s"'%attrs['xml:lang']
        if self.xmlns: xmlns=self.xmlns
        else: xmlns=NS_SERVER
        text+=' xmlns:db="%s" xmlns:stream="%s" xmlns="%s"'%(NS_DIALBACK,NS_STREAMS,xmlns)
        if attrs.has_key('version') or self.TYP=='client': text+=' version="1.0"'
        self.sendnow(text+'>')
        self.set_stream_state(STREAM__OPENED)
        if self.TYP=='client': return
        if tag<>'stream': return self.terminate_stream(STREAM_INVALID_XML)
        if ns<>NS_STREAMS: return self.terminate_stream(STREAM_INVALID_NAMESPACE)
        if self.Stream.xmlns<>self.xmlns: return self.terminate_stream(STREAM_BAD_NAMESPACE_PREFIX)
        if not attrs.has_key('to'): return self.terminate_stream(STREAM_IMPROPER_ADDRESSING)
        if attrs['to'] not in self._owner.servernames: return self.terminate_stream(STREAM_HOST_UNKNOWN)
        self.ourname=attrs['to'].lower()
        if self.TYP=='server' and attrs.has_key('version'):
            # send features
            features=Node('stream:features')
            if NS_TLS in self.waiting_features:
                features.NT.starttls.setNamespace(NS_TLS)
                features.T.starttls.NT.required
            if NS_SASL in self.waiting_features:
                features.NT.mechanisms.setNamespace(NS_SASL)
                for mec in self._owner.SASL.mechanisms:
                    features.T.mechanisms.NT.mechanism=mec
            else:
                if NS_BIND in self.waiting_features: features.NT.bind.setNamespace(NS_BIND)
                if NS_SESSION in self.waiting_features: features.NT.session.setNamespace(NS_SESSION)
            self.sendnow(features)

    def feature(self,feature):
        """ Declare some stream feature as activated one. """
        if feature not in self.features: self.features.append(feature)
        self.unfeature(feature)

    def unfeature(self,feature):
        """ Declare some feature as illegal. Illegal features can not be used.
            Example: BIND feature becomes illegal after Non-SASL auth. """
        if feature in self.waiting_features: self.waiting_features.remove(feature)

    def _stream_close(self,unregister=1):
        """ Write the closing stream tag and destroy the underlaying socket. Used internally. """
        if self._stream_state>=STREAM__CLOSED: return
        self.set_stream_state(STREAM__CLOSING)
        self.sendnow('</stream:stream>')
        self.set_stream_state(STREAM__CLOSED)
        self.push_queue()       # decompose queue really since STREAM__CLOSED
        self._owner.flush_queues()
        if unregister: self._owner.unregistersession(self)
        self._destroy_socket()

    def terminate_stream(self,error=None,unregister=1):
        """ Notify the peer about stream closure.
            Ensure that xmlstream is not brokes - i.e. if the stream isn't opened yet -
            open it before closure.
            If the error condition is specified than create a stream error and send it along with
            closing stream tag.
            Emulate receiving 'unavailable' type presence just before stream closure.
        """
        if self._stream_state>=STREAM__CLOSING: return
        if self._stream_state<STREAM__OPENED:
            self.set_stream_state(STREAM__CLOSING)
            self._stream_open()
        else:
            self.set_stream_state(STREAM__CLOSING)
            p=Presence(typ='unavailable')
            p.setNamespace(NS_CLIENT)
            self._dispatch(p,trusted=1)
        if error:
            if isinstance(error,Node): self.sendnow(error)
            else: self.sendnow(ErrorNode(error))
        self._stream_close(unregister=unregister)
        if self.slave_session:
            self.slave_session.terminate_stream(STREAM_REMOTE_CONNECTION_FAILED)

    def _destroy_socket(self):
        """ Break cyclic dependancies to let python's GC free memory right now."""
        self.Stream.dispatch=None
        self.Stream.stream_footer_received=None
        self.Stream.stream_header_received=None
        self.Stream.destroy()
        self._sock.close()
        self.set_socket_state(SOCKET_DEAD)

    def start_feature(self,f):
        """ Declare some feature as "negotiating now" to prevent other features from start negotiating. """
        if self.feature_in_process: raise "Starting feature %s over %s !"%(f,self.feature_in_process)
        self.feature_in_process=f

    def stop_feature(self,f):
        """ Declare some feature as "negotiated" to allow other features start negotiating. """
        if self.feature_in_process<>f: raise "Stopping feature %s instead of %s !"%(f,self.feature_in_process)
        self.feature_in_process=None

    def set_socket_state(self,newstate):
        """ Change the underlaying socket state.
            Socket starts with SOCKET_UNCONNECTED state
            and then proceeds (possibly) to SOCKET_ALIVE
            and then to SOCKET_DEAD """
        if self._socket_state<newstate: self._socket_state=newstate

    def set_session_state(self,newstate):
        """ Change the session state.
            Session starts with SESSION_NOT_AUTHED state
            and then comes through 
            SESSION_AUTHED, SESSION_BOUND, SESSION_OPENED and SESSION_CLOSED states.
        """
        if self._session_state<newstate:
            if self._session_state<SESSION_AUTHED and \
               newstate>=SESSION_AUTHED: self._stream_pos_queued=self._stream_pos_sent
            self._session_state=newstate

    def set_stream_state(self,newstate):
        """ Change the underlaying XML stream state
            Stream starts with STREAM__NOT_OPENED and then proceeds with
            STREAM__OPENED, STREAM__CLOSING and STREAM__CLOSED states.
            Note that some features (like TLS and SASL)
            requires stream re-start so this state can have non-linear changes. """
        if self._stream_state<newstate: self._stream_state=newstate
