##   browser.py
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

# $Id: browser.py,v 1.12 2007/05/13 17:55:14 normanr Exp $

"""Browser module provides DISCO server framework for your application.
This functionality can be used for very different purposes - from publishing
software version and supported features to building of "jabber site" that users
can navigate with their disco browsers and interact with active content.

Such functionality is achieved via registering "DISCO handlers" that are
automatically called when user requests some node of your disco tree.
"""

from dispatcher import *
from client import PlugIn

class Browser(PlugIn):
    """ WARNING! This class is for components only. It will not work in client mode!

        Standart xmpppy class that is ancestor of PlugIn and can be attached
        to your application.
        All processing will be performed in the handlers registered in the browser
        instance. You can register any number of handlers ensuring that for each
        node/jid combination only one (or none) handler registered.
        You can register static information or the fully-blown function that will
        calculate the answer dynamically.
        Example of static info (see JEP-0030, examples 13-14):
        # cl - your xmpppy connection instance.
        b=xmpp.browser.Browser()
        b.PlugIn(cl)
        items=[]
        item={}
        item['jid']='catalog.shakespeare.lit'
        item['node']='books'
        item['name']='Books by and about Shakespeare'
        items.append(item)
        item={}
        item['jid']='catalog.shakespeare.lit'
        item['node']='clothing'
        item['name']='Wear your literary taste with pride'
        items.append(item)
        item={}
        item['jid']='catalog.shakespeare.lit'
        item['node']='music'
        item['name']='Music from the time of Shakespeare'
        items.append(item)
        info={'ids':[], 'features':[]}
        b.setDiscoHandler({'items':items,'info':info})

        items should be a list of item elements.
        every item element can have any of these four keys: 'jid', 'node', 'name', 'action'
        info should be a dicionary and must have keys 'ids' and 'features'.
        Both of them should be lists:
            ids is a list of dictionaries and features is a list of text strings.
        Example (see JEP-0030, examples 1-2)
        # cl - your xmpppy connection instance.
        b=xmpp.browser.Browser()
        b.PlugIn(cl)
        items=[]
        ids=[]
        ids.append({'category':'conference','type':'text','name':'Play-Specific Chatrooms'})
        ids.append({'category':'directory','type':'chatroom','name':'Play-Specific Chatrooms'})
        features=[NS_DISCO_INFO,NS_DISCO_ITEMS,NS_MUC,NS_REGISTER,NS_SEARCH,NS_TIME,NS_VERSION]
        info={'ids':ids,'features':features}
        # info['xdata']=xmpp.protocol.DataForm() # JEP-0128
        b.setDiscoHandler({'items':[],'info':info})
    """
    def __init__(self):
        """Initialises internal variables. Used internally."""
        PlugIn.__init__(self)
        DBG_LINE='browser'
        self._exported_methods=[]
        self._handlers={'':{}}

    def plugin(self, owner):
        """ Registers it's own iq handlers in your application dispatcher instance.
            Used internally."""
        owner.RegisterHandler('iq',self._DiscoveryHandler,typ='get',ns=NS_DISCO_INFO)
        owner.RegisterHandler('iq',self._DiscoveryHandler,typ='get',ns=NS_DISCO_ITEMS)

    def plugout(self):
        """ Unregisters browser's iq handlers from your application dispatcher instance.
            Used internally."""
        self._owner.UnregisterHandler('iq',self._DiscoveryHandler,typ='get',ns=NS_DISCO_INFO)
        self._owner.UnregisterHandler('iq',self._DiscoveryHandler,typ='get',ns=NS_DISCO_ITEMS)

    def _traversePath(self,node,jid,set=0):
        """ Returns dictionary and key or None,None
            None - root node (w/o "node" attribute)
            /a/b/c - node
            /a/b/  - branch
            Set returns '' or None as the key
            get returns '' or None as the key or None as the dict.
            Used internally."""
        if self._handlers.has_key(jid): cur=self._handlers[jid]
        elif set:
            self._handlers[jid]={}
            cur=self._handlers[jid]
        else: cur=self._handlers['']
        if node is None: node=[None]
        else: node=node.replace('/',' /').split('/')
        for i in node:
            if i<>'' and cur.has_key(i): cur=cur[i]
            elif set and i<>'': cur[i]={dict:cur,str:i}; cur=cur[i]
            elif set or cur.has_key(''): return cur,''
            else: return None,None
        if cur.has_key(1) or set: return cur,1
        raise "Corrupted data"

    def setDiscoHandler(self,handler,node='',jid=''):
        """ This is the main method that you will use in this class.
            It is used to register supplied DISCO handler (or dictionary with static info)
            as handler of some disco tree branch.
            If you do not specify the node this handler will be used for all queried nodes.
            If you do not specify the jid this handler will be used for all queried JIDs.
            
            Usage:
            cl.Browser.setDiscoHandler(someDict,node,jid)
            or
            cl.Browser.setDiscoHandler(someDISCOHandler,node,jid)
            where

            someDict={
                'items':[
                          {'jid':'jid1','action':'action1','node':'node1','name':'name1'},
                          {'jid':'jid2','action':'action2','node':'node2','name':'name2'},
                          {'jid':'jid3','node':'node3','name':'name3'},
                          {'jid':'jid4','node':'node4'}
                        ],
                'info' :{
                          'ids':[
                                  {'category':'category1','type':'type1','name':'name1'},
                                  {'category':'category2','type':'type2','name':'name2'},
                                  {'category':'category3','type':'type3','name':'name3'},
                                ], 
                          'features':['feature1','feature2','feature3','feature4'], 
                          'xdata':DataForm
                        }
                     }

            and/or

            def someDISCOHandler(session,request,TYR):
                # if TYR=='items':  # returns items list of the same format as shown above
                # elif TYR=='info': # returns info dictionary of the same format as shown above
                # else: # this case is impossible for now.
        """
        self.DEBUG('Registering handler %s for "%s" node->%s'%(handler,jid,node), 'info')
        node,key=self._traversePath(node,jid,1)
        node[key]=handler

    def getDiscoHandler(self,node='',jid=''):
        """ Returns the previously registered DISCO handler
            that is resonsible for this node/jid combination.
            Used internally."""
        node,key=self._traversePath(node,jid)
        if node: return node[key]

    def delDiscoHandler(self,node='',jid=''):
        """ Unregisters DISCO handler that is resonsible for this
            node/jid combination. When handler is unregistered the branch
            is handled in the same way that it's parent branch from this moment.
        """
        node,key=self._traversePath(node,jid)
        if node:
            handler=node[key]
            del node[dict][node[str]]
            return handler

    def _DiscoveryHandler(self,conn,request):
        """ Servers DISCO iq request from the remote client.
            Automatically determines the best handler to use and calls it
            to handle the request. Used internally.
        """
        node=request.getQuerynode()
        if node:
            nodestr=node
        else:
            nodestr='None'
        handler=self.getDiscoHandler(node,request.getTo())
        if not handler:
            self.DEBUG("No Handler for request with jid->%s node->%s ns->%s"%(request.getTo().__str__().encode('utf8'),nodestr.encode('utf8'),request.getQueryNS().encode('utf8')),'error')
            conn.send(Error(request,ERR_ITEM_NOT_FOUND))
            raise NodeProcessed
        self.DEBUG("Handling request with jid->%s node->%s ns->%s"%(request.getTo().__str__().encode('utf8'),nodestr.encode('utf8'),request.getQueryNS().encode('utf8')),'ok')
        rep=request.buildReply('result')
        if node: rep.setQuerynode(node)
        q=rep.getTag('query')
        if request.getQueryNS()==NS_DISCO_ITEMS:
            # handler must return list: [{jid,action,node,name}]
            if type(handler)==dict: lst=handler['items']
            else: lst=handler(conn,request,'items')
            if lst==None:
                conn.send(Error(request,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
            for item in lst: q.addChild('item',item)
        elif request.getQueryNS()==NS_DISCO_INFO:
            if type(handler)==dict: dt=handler['info']
            else: dt=handler(conn,request,'info')
            if dt==None:
                conn.send(Error(request,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
            # handler must return dictionary:
            # {'ids':[{},{},{},{}], 'features':[fe,at,ur,es], 'xdata':DataForm}
            for id in dt['ids']: q.addChild('identity',id)
            for feature in dt['features']: q.addChild('feature',{'var':feature})
            if dt.has_key('xdata'): q.addChild(node=dt['xdata'])
        conn.send(rep)
        raise NodeProcessed
