##   roster.py
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

# $Id: roster.py,v 1.20 2005/07/13 13:22:52 snakeru Exp $

"""
Simple roster implementation. Can be used though for different tasks like
mass-renaming of contacts.
"""

from protocol import *
from client import PlugIn

class Roster(PlugIn):
    """ Defines a plenty of methods that will allow you to manage roster.
        Also automatically track presences from remote JIDs taking into 
        account that every JID can have multiple resources connected. Does not
        currently support 'error' presences.
        You can also use mapping interface for access to the internal representation of
        contacts in roster.
        """
    def __init__(self):
        """ Init internal variables. """
        PlugIn.__init__(self)
        self.DBG_LINE='roster'
        self._data = {}
        self.set=None
        self._exported_methods=[self.getRoster]

    def plugin(self,owner,request=1):
        """ Register presence and subscription trackers in the owner's dispatcher.
            Also request roster from server if the 'request' argument is set.
            Used internally."""
        self._owner.RegisterHandler('iq',self.RosterIqHandler,'result',NS_ROSTER)
        self._owner.RegisterHandler('iq',self.RosterIqHandler,'set',NS_ROSTER)
        self._owner.RegisterHandler('presence',self.PresenceHandler)
        if request: self.Request()

    def Request(self,force=0):
        """ Request roster from server if it were not yet requested 
            (or if the 'force' argument is set). """
        if self.set is None: self.set=0
        elif not force: return
        self._owner.send(Iq('get',NS_ROSTER))
        self.DEBUG('Roster requested from server','start')

    def getRoster(self):
        """ Requests roster from server if neccessary and returns self."""
        if not self.set: self.Request()
        while not self.set: self._owner.Process(10)
        return self

    def RosterIqHandler(self,dis,stanza):
        """ Subscription tracker. Used internally for setting items state in
            internal roster representation. """
        for item in stanza.getTag('query').getTags('item'):
            jid=item.getAttr('jid')
            if item.getAttr('subscription')=='remove':
                if self._data.has_key(jid): del self._data[jid]
                raise NodeProcessed             # a MUST
            self.DEBUG('Setting roster item %s...'%jid,'ok')
            if not self._data.has_key(jid): self._data[jid]={}
            self._data[jid]['name']=item.getAttr('name')
            self._data[jid]['ask']=item.getAttr('ask')
            self._data[jid]['subscription']=item.getAttr('subscription')
            self._data[jid]['groups']=[]
            if not self._data[jid].has_key('resources'): self._data[jid]['resources']={}
            for group in item.getTags('group'): self._data[jid]['groups'].append(group.getData())
        self._data[self._owner.User+'@'+self._owner.Server]={'resources':{},'name':None,'ask':None,'subscription':None,'groups':None,}
        self.set=1
        raise NodeProcessed   # a MUST. Otherwise you'll get back an <iq type='error'/>

    def PresenceHandler(self,dis,pres):
        """ Presence tracker. Used internally for setting items' resources state in
            internal roster representation. """
        jid=JID(pres.getFrom())
        if not self._data.has_key(jid.getStripped()): self._data[jid.getStripped()]={'name':None,'ask':None,'subscription':'none','groups':['Not in roster'],'resources':{}}

        item=self._data[jid.getStripped()]
        typ=pres.getType()

        if not typ:
            self.DEBUG('Setting roster item %s for resource %s...'%(jid.getStripped(),jid.getResource()),'ok')
            item['resources'][jid.getResource()]=res={'show':None,'status':None,'priority':'0','timestamp':None}
            if pres.getTag('show'): res['show']=pres.getShow()
            if pres.getTag('status'): res['status']=pres.getStatus()
            if pres.getTag('priority'): res['priority']=pres.getPriority()
            if not pres.getTimestamp(): pres.setTimestamp()
            res['timestamp']=pres.getTimestamp()
        elif typ=='unavailable' and item['resources'].has_key(jid.getResource()): del item['resources'][jid.getResource()]
        # Need to handle type='error' also

    def _getItemData(self,jid,dataname):
        """ Return specific jid's representation in internal format. Used internally. """
        jid=jid[:(jid+'/').find('/')]
        return self._data[jid][dataname]
    def _getResourceData(self,jid,dataname):
        """ Return specific jid's resource representation in internal format. Used internally. """
        if jid.find('/')+1:
            jid,resource=jid.split('/',1)
            if self._data[jid]['resources'].has_key(resource): return self._data[jid]['resources'][resource][dataname]
        elif self._data[jid]['resources'].keys():
            lastpri=-129
            for r in self._data[jid]['resources'].keys():
                if int(self._data[jid]['resources'][r]['priority'])>lastpri: resource,lastpri=r,int(self._data[jid]['resources'][r]['priority'])
            return self._data[jid]['resources'][resource][dataname]
    def delItem(self,jid):
        """ Delete contact 'jid' from roster."""
        self._owner.send(Iq('set',NS_ROSTER,payload=[Node('item',{'jid':jid,'subscription':'remove'})]))
    def getAsk(self,jid):
        """ Returns 'ask' value of contact 'jid'."""
        return self._getItemData(jid,'ask')
    def getGroups(self,jid):
        """ Returns groups list that contact 'jid' belongs to."""
        return self._getItemData(jid,'groups')
    def getName(self,jid):
        """ Returns name of contact 'jid'."""
        return self._getItemData(jid,'name')
    def getPriority(self,jid):
        """ Returns priority of contact 'jid'. 'jid' should be a full (not bare) JID."""
        return self._getResourceData(jid,'priority')
    def getRawRoster(self):
        """ Returns roster representation in internal format. """
        return self._data
    def getRawItem(self,jid):
        """ Returns roster item 'jid' representation in internal format. """
        return self._data[jid[:(jid+'/').find('/')]]
    def getShow(self, jid):
        """ Returns 'show' value of contact 'jid'. 'jid' should be a full (not bare) JID."""
        return self._getResourceData(jid,'show')
    def getStatus(self, jid):
        """ Returns 'status' value of contact 'jid'. 'jid' should be a full (not bare) JID."""
        return self._getResourceData(jid,'status')
    def getSubscription(self,jid):
        """ Returns 'subscription' value of contact 'jid'."""
        return self._getItemData(jid,'subscription')
    def getResources(self,jid):
        """ Returns list of connected resources of contact 'jid'."""
        return self._data[jid[:(jid+'/').find('/')]]['resources'].keys()
    def setItem(self,jid,name=None,groups=[]):
        """ Creates/renames contact 'jid' and sets the groups list that it now belongs to."""
        iq=Iq('set',NS_ROSTER)
        query=iq.getTag('query')
        attrs={'jid':jid}
        if name: attrs['name']=name
        item=query.setTag('item',attrs)
        for group in groups: item.addChild(node=Node('group',payload=[group]))
        self._owner.send(iq)
    def getItems(self):
        """ Return list of all [bare] JIDs that the roster is currently tracks."""
        return self._data.keys()
    def keys(self):
        """ Same as getItems. Provided for the sake of dictionary interface."""
        return self._data.keys()
    def __getitem__(self,item):
        """ Get the contact in the internal format. Raises KeyError if JID 'item' is not in roster."""
        return self._data[item]
    def getItem(self,item):
        """ Get the contact in the internal format (or None if JID 'item' is not in roster)."""
        if self._data.has_key(item): return self._data[item]
    def Subscribe(self,jid):
        """ Send subscription request to JID 'jid'."""
        self._owner.send(Presence(jid,'subscribe'))
    def Unsubscribe(self,jid):
        """ Ask for removing our subscription for JID 'jid'."""
        self._owner.send(Presence(jid,'unsubscribe'))
    def Authorize(self,jid):
        """ Authorise JID 'jid'. Works only if these JID requested auth previously. """
        self._owner.send(Presence(jid,'subscribed'))
    def Unauthorize(self,jid):
        """ Unauthorise JID 'jid'. Use for declining authorisation request 
            or for removing existing authorization. """
        self._owner.send(Presence(jid,'unsubscribed'))
