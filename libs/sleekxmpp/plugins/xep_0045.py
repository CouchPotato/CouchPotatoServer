"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""
from __future__ import with_statement

import logging

from sleekxmpp import Presence
from sleekxmpp.plugins import BasePlugin, register_plugin
from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase, JID, ET
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.matcher.xmlmask import MatchXMLMask
from sleekxmpp.exceptions import IqError, IqTimeout


log = logging.getLogger(__name__)


class MUCPresence(ElementBase):
    name = 'x'
    namespace = 'http://jabber.org/protocol/muc#user'
    plugin_attrib = 'muc'
    interfaces = set(('affiliation', 'role', 'jid', 'nick', 'room'))
    affiliations = set(('', ))
    roles = set(('', ))

    def getXMLItem(self):
        item = self.xml.find('{http://jabber.org/protocol/muc#user}item')
        if item is None:
            item = ET.Element('{http://jabber.org/protocol/muc#user}item')
            self.xml.append(item)
        return item

    def getAffiliation(self):
        #TODO if no affilation, set it to the default and return default
        item = self.getXMLItem()
        return item.get('affiliation', '')

    def setAffiliation(self, value):
        item = self.getXMLItem()
        #TODO check for valid affiliation
        item.attrib['affiliation'] = value
        return self

    def delAffiliation(self):
        item = self.getXMLItem()
        #TODO set default affiliation
        if 'affiliation' in item.attrib: del item.attrib['affiliation']
        return self

    def getJid(self):
        item = self.getXMLItem()
        return JID(item.get('jid', ''))

    def setJid(self, value):
        item = self.getXMLItem()
        if not isinstance(value, str):
            value = str(value)
        item.attrib['jid'] = value
        return self

    def delJid(self):
        item = self.getXMLItem()
        if 'jid' in item.attrib: del item.attrib['jid']
        return self

    def getRole(self):
        item = self.getXMLItem()
        #TODO get default role, set default role if none
        return item.get('role', '')

    def setRole(self, value):
        item = self.getXMLItem()
        #TODO check for valid role
        item.attrib['role'] = value
        return self

    def delRole(self):
        item = self.getXMLItem()
        #TODO set default role
        if 'role' in item.attrib: del item.attrib['role']
        return self

    def getNick(self):
        return self.parent()['from'].resource

    def getRoom(self):
        return self.parent()['from'].bare

    def setNick(self, value):
        log.warning("Cannot set nick through mucpresence plugin.")
        return self

    def setRoom(self, value):
        log.warning("Cannot set room through mucpresence plugin.")
        return self

    def delNick(self):
        log.warning("Cannot delete nick through mucpresence plugin.")
        return self

    def delRoom(self):
        log.warning("Cannot delete room through mucpresence plugin.")
        return self


class XEP_0045(BasePlugin):

    """
    Implements XEP-0045 Multi-User Chat
    """

    name = 'xep_0045'
    description = 'XEP-0045: Multi-User Chat'
    dependencies = set(['xep_0030', 'xep_0004'])

    def plugin_init(self):
        self.rooms = {}
        self.ourNicks = {}
        self.xep = '0045'
        # load MUC support in presence stanzas
        register_stanza_plugin(Presence, MUCPresence)
        self.xmpp.registerHandler(Callback('MUCPresence', MatchXMLMask("<presence xmlns='%s' />" % self.xmpp.default_ns), self.handle_groupchat_presence))
        self.xmpp.registerHandler(Callback('MUCMessage', MatchXMLMask("<message xmlns='%s' type='groupchat'><body/></message>" % self.xmpp.default_ns), self.handle_groupchat_message))
        self.xmpp.registerHandler(Callback('MUCSubject', MatchXMLMask("<message xmlns='%s' type='groupchat'><subject/></message>" % self.xmpp.default_ns), self.handle_groupchat_subject))
        self.xmpp.registerHandler(Callback('MUCConfig', MatchXMLMask("<message xmlns='%s' type='groupchat'><x xmlns='http://jabber.org/protocol/muc#user'><status/></x></message>" % self.xmpp.default_ns), self.handle_config_change))
        self.xmpp.registerHandler(Callback('MUCInvite', MatchXPath("{%s}message/{%s}x/{%s}invite" % (
            self.xmpp.default_ns,
            'http://jabber.org/protocol/muc#user',
            'http://jabber.org/protocol/muc#user')), self.handle_groupchat_invite))

    def handle_groupchat_invite(self, inv):
        """ Handle an invite into a muc.
        """
        logging.debug("MUC invite to %s from %s: %s", inv['to'], inv["from"], inv)
        if inv['from'] not in self.rooms.keys():
            self.xmpp.event("groupchat_invite", inv)

    def handle_config_change(self, msg):
        """Handle a MUC configuration change (with status code)."""
        self.xmpp.event('groupchat_config_status', msg)
        self.xmpp.event('muc::%s::config_status' % msg['from'].bare , msg)

    def handle_groupchat_presence(self, pr):
        """ Handle a presence in a muc.
        """
        got_offline = False
        got_online = False
        if pr['muc']['room'] not in self.rooms.keys():
            return
        entry = pr['muc'].getStanzaValues()
        entry['show'] = pr['show']
        entry['status'] = pr['status']
        entry['alt_nick'] = pr['nick']
        if pr['type'] == 'unavailable':
            if entry['nick'] in self.rooms[entry['room']]:
                del self.rooms[entry['room']][entry['nick']]
            got_offline = True
        else:
            if entry['nick'] not in self.rooms[entry['room']]:
                got_online = True
            self.rooms[entry['room']][entry['nick']] = entry
        log.debug("MUC presence from %s/%s : %s", entry['room'],entry['nick'], entry)
        self.xmpp.event("groupchat_presence", pr)
        self.xmpp.event("muc::%s::presence" % entry['room'], pr)
        if got_offline:
            self.xmpp.event("muc::%s::got_offline" % entry['room'], pr)
        if got_online:
            self.xmpp.event("muc::%s::got_online" % entry['room'], pr)

    def handle_groupchat_message(self, msg):
        """ Handle a message event in a muc.
        """
        self.xmpp.event('groupchat_message', msg)
        self.xmpp.event("muc::%s::message" % msg['from'].bare, msg)

    def handle_groupchat_subject(self, msg):
        """ Handle a message coming from a muc indicating
        a change of subject (or announcing it when joining the room)
        """
        self.xmpp.event('groupchat_subject', msg)

    def jidInRoom(self, room, jid):
        for nick in self.rooms[room]:
            entry = self.rooms[room][nick]
            if entry is not None and entry['jid'].full == jid:
                return True
        return False

    def getNick(self, room, jid):
        for nick in self.rooms[room]:
            entry = self.rooms[room][nick]
            if entry is not None and entry['jid'].full == jid:
                return nick

    def getRoomForm(self, room, ifrom=None):
        iq = self.xmpp.makeIqGet()
        iq['to'] = room
        if ifrom is not None:
            iq['from'] = ifrom
        query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
        iq.append(query)
        # For now, swallow errors to preserve existing API
        try:
            result = iq.send()
        except IqError:
            return False
        except IqTimeout:
            return False
        xform = result.xml.find('{http://jabber.org/protocol/muc#owner}query/{jabber:x:data}x')
        if xform is None: return False
        form = self.xmpp.plugin['old_0004'].buildForm(xform)
        return form

    def configureRoom(self, room, form=None, ifrom=None):
        if form is None:
            form = self.getRoomForm(room, ifrom=ifrom)
            #form = self.xmpp.plugin['old_0004'].makeForm(ftype='submit')
            #form.addField('FORM_TYPE', value='http://jabber.org/protocol/muc#roomconfig')
        iq = self.xmpp.makeIqSet()
        iq['to'] = room
        if ifrom is not None:
            iq['from'] = ifrom
        query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
        form = form.getXML('submit')
        query.append(form)
        iq.append(query)
        # For now, swallow errors to preserve existing API
        try:
            result = iq.send()
        except IqError:
            return False
        except IqTimeout:
            return False
        return True

    def joinMUC(self, room, nick, maxhistory="0", password='', wait=False, pstatus=None, pshow=None, pfrom=None):
        """ Join the specified room, requesting 'maxhistory' lines of history.
        """
        stanza = self.xmpp.makePresence(pto="%s/%s" % (room, nick), pstatus=pstatus, pshow=pshow, pfrom=pfrom)
        x = ET.Element('{http://jabber.org/protocol/muc}x')
        if password:
            passelement = ET.Element('{http://jabber.org/protocol/muc}password')
            passelement.text = password
            x.append(passelement)
        if maxhistory:
            history = ET.Element('{http://jabber.org/protocol/muc}history')
            if maxhistory ==  "0":
                history.attrib['maxchars'] = maxhistory
            else:
                history.attrib['maxstanzas'] = maxhistory
            x.append(history)
        stanza.append(x)
        if not wait:
            self.xmpp.send(stanza)
        else:
            #wait for our own room presence back
            expect = ET.Element("{%s}presence" % self.xmpp.default_ns, {'from':"%s/%s" % (room, nick)})
            self.xmpp.send(stanza, expect)
        self.rooms[room] = {}
        self.ourNicks[room] = nick

    def destroy(self, room, reason='', altroom = '', ifrom=None):
        iq = self.xmpp.makeIqSet()
        if ifrom is not None:
            iq['from'] = ifrom
        iq['to'] = room
        query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
        destroy = ET.Element('{http://jabber.org/protocol/muc#owner}destroy')
        if altroom:
            destroy.attrib['jid'] = altroom
        xreason = ET.Element('{http://jabber.org/protocol/muc#owner}reason')
        xreason.text = reason
        destroy.append(xreason)
        query.append(destroy)
        iq.append(query)
        # For now, swallow errors to preserve existing API
        try:
            r = iq.send()
        except IqError:
            return False
        except IqTimeout:
            return False
        return True

    def setAffiliation(self, room, jid=None, nick=None, affiliation='member', ifrom=None):
        """ Change room affiliation."""
        if affiliation not in ('outcast', 'member', 'admin', 'owner', 'none'):
            raise TypeError
        query = ET.Element('{http://jabber.org/protocol/muc#admin}query')
        if nick is not None:
            item = ET.Element('{http://jabber.org/protocol/muc#admin}item', {'affiliation':affiliation, 'nick':nick})
        else:
            item = ET.Element('{http://jabber.org/protocol/muc#admin}item', {'affiliation':affiliation, 'jid':jid})
        query.append(item)
        iq = self.xmpp.makeIqSet(query)
        iq['to'] = room
        iq['from'] = ifrom
        # For now, swallow errors to preserve existing API
        try:
            result = iq.send()
        except IqError:
            return False
        except IqTimeout:
            return False
        return True

    def invite(self, room, jid, reason='', mfrom=''):
        """ Invite a jid to a room."""
        msg = self.xmpp.makeMessage(room)
        msg['from'] = mfrom
        x = ET.Element('{http://jabber.org/protocol/muc#user}x')
        invite = ET.Element('{http://jabber.org/protocol/muc#user}invite', {'to': jid})
        if reason:
            rxml = ET.Element('{http://jabber.org/protocol/muc#user}reason')
            rxml.text = reason
            invite.append(rxml)
        x.append(invite)
        msg.append(x)
        self.xmpp.send(msg)

    def leaveMUC(self, room, nick, msg='', pfrom=None):
        """ Leave the specified room.
        """
        if msg:
            self.xmpp.sendPresence(pshow='unavailable', pto="%s/%s" % (room, nick), pstatus=msg, pfrom=pfrom)
        else:
            self.xmpp.sendPresence(pshow='unavailable', pto="%s/%s" % (room, nick), pfrom=pfrom)
        del self.rooms[room]

    def getRoomConfig(self, room, ifrom=''):
        iq = self.xmpp.makeIqGet('http://jabber.org/protocol/muc#owner')
        iq['to'] = room
        iq['from'] = ifrom
        # For now, swallow errors to preserve existing API
        try:
            result = iq.send()
        except IqError:
            raise ValueError
        except IqTimeout:
            raise ValueError
        form = result.xml.find('{http://jabber.org/protocol/muc#owner}query/{jabber:x:data}x')
        if form is None:
            raise ValueError
        return self.xmpp.plugin['xep_0004'].buildForm(form)

    def cancelConfig(self, room, ifrom=None):
        query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
        x = ET.Element('{jabber:x:data}x', type='cancel')
        query.append(x)
        iq = self.xmpp.makeIqSet(query)
        iq['to'] = room
        iq['from'] = ifrom
        iq.send()

    def setRoomConfig(self, room, config, ifrom=''):
        query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
        x = config.getXML('submit')
        query.append(x)
        iq = self.xmpp.makeIqSet(query)
        iq['to'] = room
        iq['from'] = ifrom
        iq.send()

    def getJoinedRooms(self):
        return self.rooms.keys()

    def getOurJidInRoom(self, roomJid):
        """ Return the jid we're using in a room.
        """
        return "%s/%s" % (roomJid, self.ourNicks[roomJid])

    def getJidProperty(self, room, nick, jidProperty):
        """ Get the property of a nick in a room, such as its 'jid' or 'affiliation'
            If not found, return None.
        """
        if room in self.rooms and nick in self.rooms[room] and jidProperty in self.rooms[room][nick]:
            return self.rooms[room][nick][jidProperty]
        else:
            return None

    def getRoster(self, room):
        """ Get the list of nicks in a room.
        """
        if room not in self.rooms.keys():
            return None
        return self.rooms[room].keys()


xep_0045 = XEP_0045
register_plugin(XEP_0045)
