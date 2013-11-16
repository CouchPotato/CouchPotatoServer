##   features.py 
##
##   Copyright (C) 2003-2004 Alexey "Snake" Nezhdanov
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

# $Id: features.py,v 1.25 2009/04/07 07:11:48 snakeru Exp $

"""
This module contains variable stuff that is not worth splitting into separate modules.
Here is:
    DISCO client and agents-to-DISCO and browse-to-DISCO emulators.
    IBR and password manager.
    jabber:iq:privacy methods
All these methods takes 'disp' first argument that should be already connected
(and in most cases already authorised) dispatcher instance.
"""

from protocol import *

REGISTER_DATA_RECEIVED='REGISTER DATA RECEIVED'

### DISCO ### http://jabber.org/protocol/disco ### JEP-0030 ####################
### Browse ### jabber:iq:browse ### JEP-0030 ###################################
### Agents ### jabber:iq:agents ### JEP-0030 ###################################
def _discover(disp,ns,jid,node=None,fb2b=0,fb2a=1):
    """ Try to obtain info from the remote object.
        If remote object doesn't support disco fall back to browse (if fb2b is true)
        and if it doesnt support browse (or fb2b is not true) fall back to agents protocol
        (if gb2a is true). Returns obtained info. Used internally. """
    iq=Iq(to=jid,typ='get',queryNS=ns)
    if node: iq.setQuerynode(node)
    rep=disp.SendAndWaitForResponse(iq)
    if fb2b and not isResultNode(rep): rep=disp.SendAndWaitForResponse(Iq(to=jid,typ='get',queryNS=NS_BROWSE))   # Fallback to browse
    if fb2a and not isResultNode(rep): rep=disp.SendAndWaitForResponse(Iq(to=jid,typ='get',queryNS=NS_AGENTS))   # Fallback to agents
    if isResultNode(rep): return [n for n in rep.getQueryPayload() if isinstance(n, Node)]
    return []

def discoverItems(disp,jid,node=None):
    """ Query remote object about any items that it contains. Return items list. """
    """ According to JEP-0030:
        query MAY have node attribute
        item: MUST HAVE jid attribute and MAY HAVE name, node, action attributes.
        action attribute of item can be either of remove or update value."""
    ret=[]
    for i in _discover(disp,NS_DISCO_ITEMS,jid,node):
        if i.getName()=='agent' and i.getTag('name'): i.setAttr('name',i.getTagData('name'))
        ret.append(i.attrs)
    return ret

def discoverInfo(disp,jid,node=None):
    """ Query remote object about info that it publishes. Returns identities and features lists."""
    """ According to JEP-0030:
        query MAY have node attribute
        identity: MUST HAVE category and name attributes and MAY HAVE type attribute.
        feature: MUST HAVE var attribute"""
    identities , features = [] , []
    for i in _discover(disp,NS_DISCO_INFO,jid,node):
        if i.getName()=='identity': identities.append(i.attrs)
        elif i.getName()=='feature': features.append(i.getAttr('var'))
        elif i.getName()=='agent':
            if i.getTag('name'): i.setAttr('name',i.getTagData('name'))
            if i.getTag('description'): i.setAttr('name',i.getTagData('description'))
            identities.append(i.attrs)
            if i.getTag('groupchat'): features.append(NS_GROUPCHAT)
            if i.getTag('register'): features.append(NS_REGISTER)
            if i.getTag('search'): features.append(NS_SEARCH)
    return identities , features

### Registration ### jabber:iq:register ### JEP-0077 ###########################
def getRegInfo(disp,host,info={},sync=True):
    """ Gets registration form from remote host.
        You can pre-fill the info dictionary.
        F.e. if you are requesting info on registering user joey than specify 
        info as {'username':'joey'}. See JEP-0077 for details.
        'disp' must be connected dispatcher instance."""
    iq=Iq('get',NS_REGISTER,to=host)
    for i in info.keys(): iq.setTagData(i,info[i])
    if sync:
        resp=disp.SendAndWaitForResponse(iq)
        _ReceivedRegInfo(disp.Dispatcher,resp, host)
        return resp
    else: disp.SendAndCallForResponse(iq,_ReceivedRegInfo, {'agent': host})

def _ReceivedRegInfo(con, resp, agent):
    iq=Iq('get',NS_REGISTER,to=agent)
    if not isResultNode(resp): return
    df=resp.getTag('query',namespace=NS_REGISTER).getTag('x',namespace=NS_DATA)
    if df:
        con.Event(NS_REGISTER,REGISTER_DATA_RECEIVED,(agent, DataForm(node=df)))
        return
    df=DataForm(typ='form')
    for i in resp.getQueryPayload():
        if type(i)<>type(iq): pass
        elif i.getName()=='instructions': df.addInstructions(i.getData())
        else: df.setField(i.getName()).setValue(i.getData())
    con.Event(NS_REGISTER,REGISTER_DATA_RECEIVED,(agent, df))

def register(disp,host,info):
    """ Perform registration on remote server with provided info.
        disp must be connected dispatcher instance.
        Returns true or false depending on registration result.
        If registration fails you can get additional info from the dispatcher's owner
        attributes lastErrNode, lastErr and lastErrCode.
    """
    iq=Iq('set',NS_REGISTER,to=host)
    if type(info)<>type({}): info=info.asDict()
    for i in info.keys(): iq.setTag('query').setTagData(i,info[i])
    resp=disp.SendAndWaitForResponse(iq)
    if isResultNode(resp): return 1

def unregister(disp,host):
    """ Unregisters with host (permanently removes account).
        disp must be connected and authorized dispatcher instance.
        Returns true on success."""
    resp=disp.SendAndWaitForResponse(Iq('set',NS_REGISTER,to=host,payload=[Node('remove')]))
    if isResultNode(resp): return 1

def changePasswordTo(disp,newpassword,host=None):
    """ Changes password on specified or current (if not specified) server.
        disp must be connected and authorized dispatcher instance.
        Returns true on success."""
    if not host: host=disp._owner.Server
    resp=disp.SendAndWaitForResponse(Iq('set',NS_REGISTER,to=host,payload=[Node('username',payload=[disp._owner.Server]),Node('password',payload=[newpassword])]))
    if isResultNode(resp): return 1

### Privacy ### jabber:iq:privacy ### draft-ietf-xmpp-im-19 ####################
#type=[jid|group|subscription]
#action=[allow|deny]

def getPrivacyLists(disp):
    """ Requests privacy lists from connected server.
        Returns dictionary of existing lists on success."""
    try:
        dict={'lists':[]}
        resp=disp.SendAndWaitForResponse(Iq('get',NS_PRIVACY))
        if not isResultNode(resp): return
        for list in resp.getQueryPayload():
            if list.getName()=='list': dict['lists'].append(list.getAttr('name'))
            else: dict[list.getName()]=list.getAttr('name')
        return dict
    except: pass

def getPrivacyList(disp,listname):
    """ Requests specific privacy list listname. Returns list of XML nodes (rules)
        taken from the server responce."""
    try:
        resp=disp.SendAndWaitForResponse(Iq('get',NS_PRIVACY,payload=[Node('list',{'name':listname})]))
        if isResultNode(resp): return resp.getQueryPayload()[0]
    except: pass

def setActivePrivacyList(disp,listname=None,typ='active'):
    """ Switches privacy list 'listname' to specified type.
        By default the type is 'active'. Returns true on success."""
    if listname: attrs={'name':listname}
    else: attrs={}
    resp=disp.SendAndWaitForResponse(Iq('set',NS_PRIVACY,payload=[Node(typ,attrs)]))
    if isResultNode(resp): return 1

def setDefaultPrivacyList(disp,listname=None):
    """ Sets the default privacy list as 'listname'. Returns true on success."""
    return setActivePrivacyList(disp,listname,'default')

def setPrivacyList(disp,list):
    """ Set the ruleset. 'list' should be the simpleXML node formatted
        according to RFC 3921 (XMPP-IM) (I.e. Node('list',{'name':listname},payload=[...]) )
        Returns true on success."""
    resp=disp.SendAndWaitForResponse(Iq('set',NS_PRIVACY,payload=[list]))
    if isResultNode(resp): return 1

def delPrivacyList(disp,listname):
    """ Deletes privacy list 'listname'. Returns true on success."""
    resp=disp.SendAndWaitForResponse(Iq('set',NS_PRIVACY,payload=[Node('list',{'name':listname})]))
    if isResultNode(resp): return 1
