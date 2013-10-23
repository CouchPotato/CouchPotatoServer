##   filetransfer.py 
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

# $Id: filetransfer.py,v 1.6 2004/12/25 20:06:59 snakeru Exp $

"""
This module contains IBB class that is the simple implementation of JEP-0047.
Note that this is just a transport for data. You have to negotiate data transfer before
(via StreamInitiation most probably). Unfortunately SI is not implemented yet.
"""

from protocol import *
from dispatcher import PlugIn
import base64

class IBB(PlugIn):
    """ IBB used to transfer small-sized data chunk over estabilished xmpp connection.
        Data is split into small blocks (by default 3000 bytes each), encoded as base 64
        and sent to another entity that compiles these blocks back into the data chunk.
        This is very inefficiend but should work under any circumstances. Note that 
        using IBB normally should be the last resort.
    """
    def __init__(self):
        """ Initialise internal variables. """
        PlugIn.__init__(self)
        self.DBG_LINE='ibb'
        self._exported_methods=[self.OpenStream]
        self._streams={}
        self._ampnode=Node(NS_AMP+' amp',payload=[Node('rule',{'condition':'deliver-at','value':'stored','action':'error'}),Node('rule',{'condition':'match-resource','value':'exact','action':'error'})])

    def plugin(self,owner):
        """ Register handlers for receiving incoming datastreams. Used internally. """
        self._owner.RegisterHandlerOnce('iq',self.StreamOpenReplyHandler) # Move to StreamOpen and specify stanza id
        self._owner.RegisterHandler('iq',self.IqHandler,ns=NS_IBB)
        self._owner.RegisterHandler('message',self.ReceiveHandler,ns=NS_IBB)

    def IqHandler(self,conn,stanza):
        """ Handles streams state change. Used internally. """
        typ=stanza.getType()
        self.DEBUG('IqHandler called typ->%s'%typ,'info')
        if typ=='set' and stanza.getTag('open',namespace=NS_IBB): self.StreamOpenHandler(conn,stanza)
        elif typ=='set' and stanza.getTag('close',namespace=NS_IBB): self.StreamCloseHandler(conn,stanza)
        elif typ=='result': self.StreamCommitHandler(conn,stanza)
        elif typ=='error': self.StreamOpenReplyHandler(conn,stanza)
        else: conn.send(Error(stanza,ERR_BAD_REQUEST))
        raise NodeProcessed

    def StreamOpenHandler(self,conn,stanza):
        """ Handles opening of new incoming stream. Used internally. """
        """
<iq type='set' 
    from='romeo@montague.net/orchard'
    to='juliet@capulet.com/balcony'
    id='inband_1'>
  <open sid='mySID' 
        block-size='4096'
        xmlns='http://jabber.org/protocol/ibb'/>
</iq>
"""
        err=None
        sid,blocksize=stanza.getTagAttr('open','sid'),stanza.getTagAttr('open','block-size')
        self.DEBUG('StreamOpenHandler called sid->%s blocksize->%s'%(sid,blocksize),'info')
        try: blocksize=int(blocksize)
        except: err=ERR_BAD_REQUEST
        if not sid or not blocksize: err=ERR_BAD_REQUEST
        elif sid in self._streams.keys(): err=ERR_UNEXPECTED_REQUEST
        if err: rep=Error(stanza,err)
        else:
            self.DEBUG("Opening stream: id %s, block-size %s"%(sid,blocksize),'info')
            rep=Protocol('iq',stanza.getFrom(),'result',stanza.getTo(),{'id':stanza.getID()})
            self._streams[sid]={'direction':'<'+str(stanza.getFrom()),'block-size':blocksize,'fp':open('/tmp/xmpp_file_'+sid,'w'),'seq':0,'syn_id':stanza.getID()}
        conn.send(rep)

    def OpenStream(self,sid,to,fp,blocksize=3000):
        """ Start new stream. You should provide stream id 'sid', the endpoind jid 'to',
            the file object containing info for send 'fp'. Also the desired blocksize can be specified.
            Take into account that recommended stanza size is 4k and IBB uses base64 encoding
            that increases size of data by 1/3."""
        if sid in self._streams.keys(): return
        if not JID(to).getResource(): return
        self._streams[sid]={'direction':'|>'+to,'block-size':blocksize,'fp':fp,'seq':0}
        self._owner.RegisterCycleHandler(self.SendHandler)
        syn=Protocol('iq',to,'set',payload=[Node(NS_IBB+' open',{'sid':sid,'block-size':blocksize})])
        self._owner.send(syn)
        self._streams[sid]['syn_id']=syn.getID()
        return self._streams[sid]

    def SendHandler(self,conn):
        """ Send next portion of data if it is time to do it. Used internally. """
        self.DEBUG('SendHandler called','info')
        for sid in self._streams.keys():
            stream=self._streams[sid]
            if stream['direction'][:2]=='|>': cont=1
            elif stream['direction'][0]=='>':
                chunk=stream['fp'].read(stream['block-size'])
                if chunk:
                    datanode=Node(NS_IBB+' data',{'sid':sid,'seq':stream['seq']},base64.encodestring(chunk))
                    stream['seq']+=1
                    if stream['seq']==65536: stream['seq']=0
                    conn.send(Protocol('message',stream['direction'][1:],payload=[datanode,self._ampnode]))
                else:
                    """ notify the other side about stream closing
                        notify the local user about sucessfull send
                        delete the local stream"""
                    conn.send(Protocol('iq',stream['direction'][1:],'set',payload=[Node(NS_IBB+' close',{'sid':sid})]))
                    conn.Event(self.DBG_LINE,'SUCCESSFULL SEND',stream)
                    del self._streams[sid]
                    self._owner.UnregisterCycleHandler(self.SendHandler)

                    """
<message from='romeo@montague.net/orchard' to='juliet@capulet.com/balcony' id='msg1'>
  <data xmlns='http://jabber.org/protocol/ibb' sid='mySID' seq='0'>
    qANQR1DBwU4DX7jmYZnncmUQB/9KuKBddzQH+tZ1ZywKK0yHKnq57kWq+RFtQdCJ
    WpdWpR0uQsuJe7+vh3NWn59/gTc5MDlX8dS9p0ovStmNcyLhxVgmqS8ZKhsblVeu
    IpQ0JgavABqibJolc3BKrVtVV1igKiX/N7Pi8RtY1K18toaMDhdEfhBRzO/XB0+P
    AQhYlRjNacGcslkhXqNjK5Va4tuOAPy2n1Q8UUrHbUd0g+xJ9Bm0G0LZXyvCWyKH
    kuNEHFQiLuCY6Iv0myq6iX6tjuHehZlFSh80b5BVV9tNLwNR5Eqz1klxMhoghJOA
  </data>
  <amp xmlns='http://jabber.org/protocol/amp'>
    <rule condition='deliver-at' value='stored' action='error'/>
    <rule condition='match-resource' value='exact' action='error'/>
  </amp>
</message>
"""

    def ReceiveHandler(self,conn,stanza):
        """ Receive next portion of incoming datastream and store it write
            it to temporary file. Used internally.
        """
        sid,seq,data=stanza.getTagAttr('data','sid'),stanza.getTagAttr('data','seq'),stanza.getTagData('data')
        self.DEBUG('ReceiveHandler called sid->%s seq->%s'%(sid,seq),'info')
        try: seq=int(seq); data=base64.decodestring(data)
        except: seq=''; data=''
        err=None
        if not sid in self._streams.keys(): err=ERR_ITEM_NOT_FOUND
        else:
            stream=self._streams[sid]
            if not data: err=ERR_BAD_REQUEST
            elif seq<>stream['seq']: err=ERR_UNEXPECTED_REQUEST
            else:
                self.DEBUG('Successfull receive sid->%s %s+%s bytes'%(sid,stream['fp'].tell(),len(data)),'ok')
                stream['seq']+=1
                stream['fp'].write(data)
        if err:
            self.DEBUG('Error on receive: %s'%err,'error')
            conn.send(Error(Iq(to=stanza.getFrom(),frm=stanza.getTo(),payload=[Node(NS_IBB+' close')]),err,reply=0))

    def StreamCloseHandler(self,conn,stanza):
        """ Handle stream closure due to all data transmitted.
            Raise xmpppy event specifying successfull data receive. """
        sid=stanza.getTagAttr('close','sid')
        self.DEBUG('StreamCloseHandler called sid->%s'%sid,'info')
        if sid in self._streams.keys():
            conn.send(stanza.buildReply('result'))
            conn.Event(self.DBG_LINE,'SUCCESSFULL RECEIVE',self._streams[sid])
            del self._streams[sid]
        else: conn.send(Error(stanza,ERR_ITEM_NOT_FOUND))

    def StreamBrokenHandler(self,conn,stanza):
        """ Handle stream closure due to all some error while receiving data.
            Raise xmpppy event specifying unsuccessfull data receive. """
        syn_id=stanza.getID()
        self.DEBUG('StreamBrokenHandler called syn_id->%s'%syn_id,'info')
        for sid in self._streams.keys():
            stream=self._streams[sid]
            if stream['syn_id']==syn_id:
                if stream['direction'][0]=='<': conn.Event(self.DBG_LINE,'ERROR ON RECEIVE',stream)
                else: conn.Event(self.DBG_LINE,'ERROR ON SEND',stream)
                del self._streams[sid]

    def StreamOpenReplyHandler(self,conn,stanza):
        """ Handle remote side reply about is it agree or not to receive our datastream.
            Used internally. Raises xmpppy event specfiying if the data transfer
            is agreed upon."""
        syn_id=stanza.getID()
        self.DEBUG('StreamOpenReplyHandler called syn_id->%s'%syn_id,'info')
        for sid in self._streams.keys():
            stream=self._streams[sid]
            if stream['syn_id']==syn_id:
                if stanza.getType()=='error':
                    if stream['direction'][0]=='<': conn.Event(self.DBG_LINE,'ERROR ON RECEIVE',stream)
                    else: conn.Event(self.DBG_LINE,'ERROR ON SEND',stream)
                    del self._streams[sid]
                elif stanza.getType()=='result':
                    if stream['direction'][0]=='|':
                        stream['direction']=stream['direction'][1:]
                        conn.Event(self.DBG_LINE,'STREAM COMMITTED',stream)
                    else: conn.send(Error(stanza,ERR_UNEXPECTED_REQUEST))
