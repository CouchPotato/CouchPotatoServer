##   protocol.py 
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

# $Id: protocol.py,v 1.60 2009/04/07 11:14:28 snakeru Exp $

"""
Protocol module contains tools that is needed for processing of 
xmpp-related data structures.
"""

from simplexml import Node,ustr
import time
NS_ACTIVITY         ='http://jabber.org/protocol/activity'                  # XEP-0108
NS_ADDRESS          ='http://jabber.org/protocol/address'                   # XEP-0033
NS_ADMIN            ='http://jabber.org/protocol/admin'                     # XEP-0133
NS_ADMIN_ADD_USER               =NS_ADMIN+'#add-user'                       # XEP-0133
NS_ADMIN_DELETE_USER            =NS_ADMIN+'#delete-user'                    # XEP-0133
NS_ADMIN_DISABLE_USER           =NS_ADMIN+'#disable-user'                   # XEP-0133
NS_ADMIN_REENABLE_USER          =NS_ADMIN+'#reenable-user'                  # XEP-0133
NS_ADMIN_END_USER_SESSION       =NS_ADMIN+'#end-user-session'               # XEP-0133
NS_ADMIN_GET_USER_PASSWORD      =NS_ADMIN+'#get-user-password'              # XEP-0133
NS_ADMIN_CHANGE_USER_PASSWORD   =NS_ADMIN+'#change-user-password'           # XEP-0133
NS_ADMIN_GET_USER_ROSTER        =NS_ADMIN+'#get-user-roster'                # XEP-0133
NS_ADMIN_GET_USER_LASTLOGIN     =NS_ADMIN+'#get-user-lastlogin'             # XEP-0133
NS_ADMIN_USER_STATS             =NS_ADMIN+'#user-stats'                     # XEP-0133
NS_ADMIN_EDIT_BLACKLIST         =NS_ADMIN+'#edit-blacklist'                 # XEP-0133
NS_ADMIN_EDIT_WHITELIST         =NS_ADMIN+'#edit-whitelist'                 # XEP-0133
NS_ADMIN_REGISTERED_USERS_NUM   =NS_ADMIN+'#get-registered-users-num'       # XEP-0133
NS_ADMIN_DISABLED_USERS_NUM     =NS_ADMIN+'#get-disabled-users-num'         # XEP-0133
NS_ADMIN_ONLINE_USERS_NUM       =NS_ADMIN+'#get-online-users-num'           # XEP-0133
NS_ADMIN_ACTIVE_USERS_NUM       =NS_ADMIN+'#get-active-users-num'           # XEP-0133
NS_ADMIN_IDLE_USERS_NUM         =NS_ADMIN+'#get-idle-users-num'             # XEP-0133
NS_ADMIN_REGISTERED_USERS_LIST  =NS_ADMIN+'#get-registered-users-list'      # XEP-0133
NS_ADMIN_DISABLED_USERS_LIST    =NS_ADMIN+'#get-disabled-users-list'        # XEP-0133
NS_ADMIN_ONLINE_USERS_LIST      =NS_ADMIN+'#get-online-users-list'          # XEP-0133
NS_ADMIN_ACTIVE_USERS_LIST      =NS_ADMIN+'#get-active-users-list'          # XEP-0133
NS_ADMIN_IDLE_USERS_LIST        =NS_ADMIN+'#get-idle-users-list'            # XEP-0133
NS_ADMIN_ANNOUNCE               =NS_ADMIN+'#announce'                       # XEP-0133
NS_ADMIN_SET_MOTD               =NS_ADMIN+'#set-motd'                       # XEP-0133
NS_ADMIN_EDIT_MOTD              =NS_ADMIN+'#edit-motd'                      # XEP-0133
NS_ADMIN_DELETE_MOTD            =NS_ADMIN+'#delete-motd'                    # XEP-0133
NS_ADMIN_SET_WELCOME            =NS_ADMIN+'#set-welcome'                    # XEP-0133
NS_ADMIN_DELETE_WELCOME         =NS_ADMIN+'#delete-welcome'                 # XEP-0133
NS_ADMIN_EDIT_ADMIN             =NS_ADMIN+'#edit-admin'                     # XEP-0133
NS_ADMIN_RESTART                =NS_ADMIN+'#restart'                        # XEP-0133
NS_ADMIN_SHUTDOWN               =NS_ADMIN+'#shutdown'                       # XEP-0133
NS_AGENTS           ='jabber:iq:agents'                                     # XEP-0094 (historical)
NS_AMP              ='http://jabber.org/protocol/amp'                       # XEP-0079
NS_AMP_ERRORS                   =NS_AMP+'#errors'                           # XEP-0079
NS_AUTH             ='jabber:iq:auth'                                       # XEP-0078
NS_AVATAR           ='jabber:iq:avatar'                                     # XEP-0008 (historical)
NS_BIND             ='urn:ietf:params:xml:ns:xmpp-bind'                     # RFC 3920
NS_BROWSE           ='jabber:iq:browse'                                     # XEP-0011 (historical)
NS_BYTESTREAM       ='http://jabber.org/protocol/bytestreams'               # XEP-0065
NS_CAPS             ='http://jabber.org/protocol/caps'                      # XEP-0115
NS_CHATSTATES       ='http://jabber.org/protocol/chatstates'                # XEP-0085
NS_CLIENT           ='jabber:client'                                        # RFC 3921
NS_COMMANDS         ='http://jabber.org/protocol/commands'                  # XEP-0050
NS_COMPONENT_ACCEPT ='jabber:component:accept'                              # XEP-0114
NS_COMPONENT_1      ='http://jabberd.jabberstudio.org/ns/component/1.0'     # Jabberd2
NS_COMPRESS         ='http://jabber.org/protocol/compress'                  # XEP-0138
NS_DATA             ='jabber:x:data'                                        # XEP-0004
NS_DATA_LAYOUT      ='http://jabber.org/protocol/xdata-layout'              # XEP-0141
NS_DATA_VALIDATE    ='http://jabber.org/protocol/xdata-validate'            # XEP-0122
NS_DELAY            ='jabber:x:delay'                                       # XEP-0091 (deprecated)
NS_DIALBACK         ='jabber:server:dialback'                               # RFC 3921
NS_DISCO            ='http://jabber.org/protocol/disco'                     # XEP-0030
NS_DISCO_INFO                   =NS_DISCO+'#info'                           # XEP-0030
NS_DISCO_ITEMS                  =NS_DISCO+'#items'                          # XEP-0030
NS_ENCRYPTED        ='jabber:x:encrypted'                                   # XEP-0027
NS_EVENT            ='jabber:x:event'                                       # XEP-0022 (deprecated)
NS_FEATURE          ='http://jabber.org/protocol/feature-neg'               # XEP-0020
NS_FILE             ='http://jabber.org/protocol/si/profile/file-transfer'  # XEP-0096
NS_GATEWAY          ='jabber:iq:gateway'                                    # XEP-0100
NS_GEOLOC           ='http://jabber.org/protocol/geoloc'                    # XEP-0080
NS_GROUPCHAT        ='gc-1.0'                                               # XEP-0045
NS_HTTP_BIND        ='http://jabber.org/protocol/httpbind'                  # XEP-0124
NS_IBB              ='http://jabber.org/protocol/ibb'                       # XEP-0047
NS_INVISIBLE        ='presence-invisible'                                   # Jabberd2
NS_IQ               ='iq'                                                   # Jabberd2
NS_LAST             ='jabber:iq:last'                                       # XEP-0012
NS_MESSAGE          ='message'                                              # Jabberd2
NS_MOOD             ='http://jabber.org/protocol/mood'                      # XEP-0107
NS_MUC              ='http://jabber.org/protocol/muc'                       # XEP-0045
NS_MUC_ADMIN                    =NS_MUC+'#admin'                            # XEP-0045
NS_MUC_OWNER                    =NS_MUC+'#owner'                            # XEP-0045
NS_MUC_UNIQUE                   =NS_MUC+'#unique'                           # XEP-0045
NS_MUC_USER                     =NS_MUC+'#user'                             # XEP-0045
NS_MUC_REGISTER                 =NS_MUC+'#register'                         # XEP-0045
NS_MUC_REQUEST                  =NS_MUC+'#request'                          # XEP-0045
NS_MUC_ROOMCONFIG               =NS_MUC+'#roomconfig'                       # XEP-0045
NS_MUC_ROOMINFO                 =NS_MUC+'#roominfo'                         # XEP-0045
NS_MUC_ROOMS                    =NS_MUC+'#rooms'                            # XEP-0045
NS_MUC_TRAFIC                   =NS_MUC+'#traffic'                          # XEP-0045
NS_NICK             ='http://jabber.org/protocol/nick'                      # XEP-0172
NS_OFFLINE          ='http://jabber.org/protocol/offline'                   # XEP-0013
NS_PHYSLOC          ='http://jabber.org/protocol/physloc'                   # XEP-0112
NS_PRESENCE         ='presence'                                             # Jabberd2
NS_PRIVACY          ='jabber:iq:privacy'                                    # RFC 3921
NS_PRIVATE          ='jabber:iq:private'                                    # XEP-0049
NS_PUBSUB           ='http://jabber.org/protocol/pubsub'                    # XEP-0060
NS_REGISTER         ='jabber:iq:register'                                   # XEP-0077
NS_RC               ='http://jabber.org/protocol/rc'                        # XEP-0146
NS_ROSTER           ='jabber:iq:roster'                                     # RFC 3921
NS_ROSTERX          ='http://jabber.org/protocol/rosterx'                   # XEP-0144
NS_RPC              ='jabber:iq:rpc'                                        # XEP-0009
NS_SASL             ='urn:ietf:params:xml:ns:xmpp-sasl'                     # RFC 3920
NS_SEARCH           ='jabber:iq:search'                                     # XEP-0055
NS_SERVER           ='jabber:server'                                        # RFC 3921
NS_SESSION          ='urn:ietf:params:xml:ns:xmpp-session'                  # RFC 3921
NS_SI               ='http://jabber.org/protocol/si'                        # XEP-0096
NS_SI_PUB           ='http://jabber.org/protocol/sipub'                     # XEP-0137
NS_SIGNED           ='jabber:x:signed'                                      # XEP-0027
NS_STANZAS          ='urn:ietf:params:xml:ns:xmpp-stanzas'                  # RFC 3920
NS_STREAMS          ='http://etherx.jabber.org/streams'                     # RFC 3920
NS_TIME             ='jabber:iq:time'                                       # XEP-0090 (deprecated)
NS_TLS              ='urn:ietf:params:xml:ns:xmpp-tls'                      # RFC 3920
NS_VACATION         ='http://jabber.org/protocol/vacation'                  # XEP-0109
NS_VCARD            ='vcard-temp'                                           # XEP-0054
NS_VCARD_UPDATE     ='vcard-temp:x:update'                                  # XEP-0153
NS_VERSION          ='jabber:iq:version'                                    # XEP-0092
NS_WAITINGLIST      ='http://jabber.org/protocol/waitinglist'               # XEP-0130
NS_XHTML_IM         ='http://jabber.org/protocol/xhtml-im'                  # XEP-0071
NS_XMPP_STREAMS     ='urn:ietf:params:xml:ns:xmpp-streams'                  # RFC 3920

xmpp_stream_error_conditions="""
bad-format --  --  -- The entity has sent XML that cannot be processed.
bad-namespace-prefix --  --  -- The entity has sent a namespace prefix that is unsupported, or has sent no namespace prefix on an element that requires such a prefix.
conflict --  --  -- The server is closing the active stream for this entity because a new stream has been initiated that conflicts with the existing stream.
connection-timeout --  --  -- The entity has not generated any traffic over the stream for some period of time.
host-gone --  --  -- The value of the 'to' attribute provided by the initiating entity in the stream header corresponds to a hostname that is no longer hosted by the server.
host-unknown --  --  -- The value of the 'to' attribute provided by the initiating entity in the stream header does not correspond to a hostname that is hosted by the server.
improper-addressing --  --  -- A stanza sent between two servers lacks a 'to' or 'from' attribute (or the attribute has no value).
internal-server-error --  --  -- The server has experienced a misconfiguration or an otherwise-undefined internal error that prevents it from servicing the stream.
invalid-from -- cancel --  -- The JID or hostname provided in a 'from' address does not match an authorized JID or validated domain negotiated between servers via SASL or dialback, or between a client and a server via authentication and resource authorization.
invalid-id --  --  -- The stream ID or dialback ID is invalid or does not match an ID previously provided.
invalid-namespace --  --  -- The streams namespace name is something other than "http://etherx.jabber.org/streams" or the dialback namespace name is something other than "jabber:server:dialback".
invalid-xml --  --  -- The entity has sent invalid XML over the stream to a server that performs validation.
not-authorized --  --  -- The entity has attempted to send data before the stream has been authenticated, or otherwise is not authorized to perform an action related to stream negotiation.
policy-violation --  --  -- The entity has violated some local service policy.
remote-connection-failed --  --  -- The server is unable to properly connect to a remote resource that is required for authentication or authorization.
resource-constraint --  --  -- The server lacks the system resources necessary to service the stream.
restricted-xml --  --  -- The entity has attempted to send restricted XML features such as a comment, processing instruction, DTD, entity reference, or unescaped character.
see-other-host --  --  -- The server will not provide service to the initiating entity but is redirecting traffic to another host.
system-shutdown --  --  -- The server is being shut down and all active streams are being closed.
undefined-condition --  --  -- The error condition is not one of those defined by the other conditions in this list.
unsupported-encoding --  --  -- The initiating entity has encoded the stream in an encoding that is not supported by the server.
unsupported-stanza-type --  --  -- The initiating entity has sent a first-level child of the stream that is not supported by the server.
unsupported-version --  --  -- The value of the 'version' attribute provided by the initiating entity in the stream header specifies a version of XMPP that is not supported by the server.
xml-not-well-formed --  --  -- The initiating entity has sent XML that is not well-formed."""
xmpp_stanza_error_conditions="""
bad-request -- 400 -- modify -- The sender has sent XML that is malformed or that cannot be processed.
conflict -- 409 -- cancel -- Access cannot be granted because an existing resource or session exists with the same name or address.
feature-not-implemented -- 501 -- cancel -- The feature requested is not implemented by the recipient or server and therefore cannot be processed.
forbidden -- 403 -- auth -- The requesting entity does not possess the required permissions to perform the action.
gone -- 302 -- modify -- The recipient or server can no longer be contacted at this address.
internal-server-error -- 500 -- wait -- The server could not process the stanza because of a misconfiguration or an otherwise-undefined internal server error.
item-not-found -- 404 -- cancel -- The addressed JID or item requested cannot be found.
jid-malformed -- 400 -- modify -- The value of the 'to' attribute in the sender's stanza does not adhere to the syntax defined in Addressing Scheme.
not-acceptable -- 406 -- cancel -- The recipient or server understands the request but is refusing to process it because it does not meet criteria defined by the recipient or server.
not-allowed -- 405 -- cancel -- The recipient or server does not allow any entity to perform the action.
not-authorized -- 401 -- auth -- The sender must provide proper credentials before being allowed to perform the action, or has provided improper credentials.
payment-required -- 402 -- auth -- The requesting entity is not authorized to access the requested service because payment is required.
recipient-unavailable -- 404 -- wait -- The intended recipient is temporarily unavailable.
redirect -- 302 -- modify -- The recipient or server is redirecting requests for this information to another entity.
registration-required -- 407 -- auth -- The requesting entity is not authorized to access the requested service because registration is required.
remote-server-not-found -- 404 -- cancel -- A remote server or service specified as part or all of the JID of the intended recipient does not exist.
remote-server-timeout -- 504 -- wait -- A remote server or service specified as part or all of the JID of the intended recipient could not be contacted within a reasonable amount of time.
resource-constraint -- 500 -- wait -- The server or recipient lacks the system resources necessary to service the request.
service-unavailable -- 503 -- cancel -- The server or recipient does not currently provide the requested service.
subscription-required -- 407 -- auth -- The requesting entity is not authorized to access the requested service because a subscription is required.
undefined-condition -- 500 --  -- 
unexpected-request -- 400 -- wait -- The recipient or server understood the request but was not expecting it at this time (e.g., the request was out of order)."""
sasl_error_conditions="""
aborted --  --  -- The receiving entity acknowledges an <abort/> element sent by the initiating entity; sent in reply to the <abort/> element.
incorrect-encoding --  --  -- The data provided by the initiating entity could not be processed because the [BASE64]Josefsson, S., The Base16, Base32, and Base64 Data Encodings, July 2003. encoding is incorrect (e.g., because the encoding does not adhere to the definition in Section 3 of [BASE64]Josefsson, S., The Base16, Base32, and Base64 Data Encodings, July 2003.); sent in reply to a <response/> element or an <auth/> element with initial response data.
invalid-authzid --  --  -- The authzid provided by the initiating entity is invalid, either because it is incorrectly formatted or because the initiating entity does not have permissions to authorize that ID; sent in reply to a <response/> element or an <auth/> element with initial response data.
invalid-mechanism --  --  -- The initiating entity did not provide a mechanism or requested a mechanism that is not supported by the receiving entity; sent in reply to an <auth/> element.
mechanism-too-weak --  --  -- The mechanism requested by the initiating entity is weaker than server policy permits for that initiating entity; sent in reply to a <response/> element or an <auth/> element with initial response data.
not-authorized --  --  -- The authentication failed because the initiating entity did not provide valid credentials (this includes but is not limited to the case of an unknown username); sent in reply to a <response/> element or an <auth/> element with initial response data.
temporary-auth-failure --  --  -- The authentication failed because of a temporary error condition within the receiving entity; sent in reply to an <auth/> element or <response/> element."""

ERRORS,_errorcodes={},{}
for ns,errname,errpool in [(NS_XMPP_STREAMS,'STREAM',xmpp_stream_error_conditions),
                           (NS_STANZAS     ,'ERR'   ,xmpp_stanza_error_conditions),
                           (NS_SASL        ,'SASL'  ,sasl_error_conditions)]:
    for err in errpool.split('\n')[1:]:
        cond,code,typ,text=err.split(' -- ')
        name=errname+'_'+cond.upper().replace('-','_')
        locals()[name]=ns+' '+cond
        ERRORS[ns+' '+cond]=[code,typ,text]
        if code: _errorcodes[code]=cond
del ns,errname,errpool,err,cond,code,typ,text

def isResultNode(node):
    """ Returns true if the node is a positive reply. """
    return node and node.getType()=='result'
def isErrorNode(node):
    """ Returns true if the node is a negative reply. """
    return node and node.getType()=='error'

class NodeProcessed(Exception):
    """ Exception that should be raised by handler when the handling should be stopped. """
class StreamError(Exception):
    """ Base exception class for stream errors."""
class BadFormat(StreamError): pass
class BadNamespacePrefix(StreamError): pass
class Conflict(StreamError): pass
class ConnectionTimeout(StreamError): pass
class HostGone(StreamError): pass
class HostUnknown(StreamError): pass
class ImproperAddressing(StreamError): pass
class InternalServerError(StreamError): pass
class InvalidFrom(StreamError): pass
class InvalidID(StreamError): pass
class InvalidNamespace(StreamError): pass
class InvalidXML(StreamError): pass
class NotAuthorized(StreamError): pass
class PolicyViolation(StreamError): pass
class RemoteConnectionFailed(StreamError): pass
class ResourceConstraint(StreamError): pass
class RestrictedXML(StreamError): pass
class SeeOtherHost(StreamError): pass
class SystemShutdown(StreamError): pass
class UndefinedCondition(StreamError): pass
class UnsupportedEncoding(StreamError): pass
class UnsupportedStanzaType(StreamError): pass
class UnsupportedVersion(StreamError): pass
class XMLNotWellFormed(StreamError): pass

stream_exceptions = {'bad-format': BadFormat,
                     'bad-namespace-prefix': BadNamespacePrefix,
                     'conflict': Conflict,
                     'connection-timeout': ConnectionTimeout,
                     'host-gone': HostGone,
                     'host-unknown': HostUnknown,
                     'improper-addressing': ImproperAddressing,
                     'internal-server-error': InternalServerError,
                     'invalid-from': InvalidFrom,
                     'invalid-id': InvalidID,
                     'invalid-namespace': InvalidNamespace,
                     'invalid-xml': InvalidXML,
                     'not-authorized': NotAuthorized,
                     'policy-violation': PolicyViolation,
                     'remote-connection-failed': RemoteConnectionFailed,
                     'resource-constraint': ResourceConstraint,
                     'restricted-xml': RestrictedXML,
                     'see-other-host': SeeOtherHost,
                     'system-shutdown': SystemShutdown,
                     'undefined-condition': UndefinedCondition,
                     'unsupported-encoding': UnsupportedEncoding,
                     'unsupported-stanza-type': UnsupportedStanzaType,
                     'unsupported-version': UnsupportedVersion,
                     'xml-not-well-formed': XMLNotWellFormed}

class JID:
    """ JID object. JID can be built from string, modified, compared, serialised into string. """
    def __init__(self, jid=None, node='', domain='', resource=''):
        """ Constructor. JID can be specified as string (jid argument) or as separate parts.
            Examples:
            JID('node@domain/resource')
            JID(node='node',domain='domain.org')
        """
        if not jid and not domain: raise ValueError('JID must contain at least domain name')
        elif type(jid)==type(self): self.node,self.domain,self.resource=jid.node,jid.domain,jid.resource
        elif domain: self.node,self.domain,self.resource=node,domain,resource
        else:
            if jid.find('@')+1: self.node,jid=jid.split('@',1)
            else: self.node=''
            if jid.find('/')+1: self.domain,self.resource=jid.split('/',1)
            else: self.domain,self.resource=jid,''
    def getNode(self):
        """ Return the node part of the JID """
        return self.node
    def setNode(self,node):
        """ Set the node part of the JID to new value. Specify None to remove the node part."""
        self.node=node.lower()
    def getDomain(self):
        """ Return the domain part of the JID """
        return self.domain
    def setDomain(self,domain):
        """ Set the domain part of the JID to new value."""
        self.domain=domain.lower()
    def getResource(self):
        """ Return the resource part of the JID """
        return self.resource
    def setResource(self,resource):
        """ Set the resource part of the JID to new value. Specify None to remove the resource part."""
        self.resource=resource
    def getStripped(self):
        """ Return the bare representation of JID. I.e. string value w/o resource. """
        return self.__str__(0)
    def __eq__(self, other):
        """ Compare the JID to another instance or to string for equality. """
        try: other=JID(other)
        except ValueError: return 0
        return self.resource==other.resource and self.__str__(0) == other.__str__(0)
    def __ne__(self, other):
        """ Compare the JID to another instance or to string for non-equality. """
        return not self.__eq__(other)
    def bareMatch(self, other):
        """ Compare the node and domain parts of the JID's for equality. """
        return self.__str__(0) == JID(other).__str__(0)
    def __str__(self,wresource=1):
        """ Serialise JID into string. """
        if self.node: jid=self.node+'@'+self.domain
        else: jid=self.domain
        if wresource and self.resource: return jid+'/'+self.resource
        return jid
    def __hash__(self):
        """ Produce hash of the JID, Allows to use JID objects as keys of the dictionary. """
        return hash(self.__str__())

class Protocol(Node):
    """ A "stanza" object class. Contains methods that are common for presences, iqs and messages. """
    def __init__(self, name=None, to=None, typ=None, frm=None, attrs={}, payload=[], timestamp=None, xmlns=None, node=None):
        """ Constructor, name is the name of the stanza i.e. 'message' or 'presence' or 'iq'.
            to is the value of 'to' attribure, 'typ' - 'type' attribute
            frn - from attribure, attrs - other attributes mapping, payload - same meaning as for simplexml payload definition
            timestamp - the time value that needs to be stamped over stanza
            xmlns - namespace of top stanza node
            node - parsed or unparsed stana to be taken as prototype.
        """
        if not attrs: attrs={}
        if to: attrs['to']=to
        if frm: attrs['from']=frm
        if typ: attrs['type']=typ
        Node.__init__(self, tag=name, attrs=attrs, payload=payload, node=node)
        if not node and xmlns: self.setNamespace(xmlns)
        if self['to']: self.setTo(self['to'])
        if self['from']: self.setFrom(self['from'])
        if node and type(self)==type(node) and self.__class__==node.__class__ and self.attrs.has_key('id'): del self.attrs['id']
        self.timestamp=None
        for x in self.getTags('x',namespace=NS_DELAY):
            try:
                if not self.getTimestamp() or x.getAttr('stamp')<self.getTimestamp(): self.setTimestamp(x.getAttr('stamp'))
            except: pass
        if timestamp is not None: self.setTimestamp(timestamp)  # To auto-timestamp stanza just pass timestamp=''
    def getTo(self):
        """ Return value of the 'to' attribute. """
        try: return self['to']
        except: return None
    def getFrom(self):
        """ Return value of the 'from' attribute. """
        try: return self['from']
        except: return None
    def getTimestamp(self):
        """ Return the timestamp in the 'yyyymmddThhmmss' format. """
        return self.timestamp
    def getID(self):
        """ Return the value of the 'id' attribute. """
        return self.getAttr('id')
    def setTo(self,val):
        """ Set the value of the 'to' attribute. """
        self.setAttr('to', JID(val))
    def getType(self):
        """ Return the value of the 'type' attribute. """
        return self.getAttr('type')
    def setFrom(self,val):
        """ Set the value of the 'from' attribute. """
        self.setAttr('from', JID(val))
    def setType(self,val):
        """ Set the value of the 'type' attribute. """
        self.setAttr('type', val)
    def setID(self,val):
        """ Set the value of the 'id' attribute. """
        self.setAttr('id', val)
    def getError(self):
        """ Return the error-condition (if present) or the textual description of the error (otherwise). """
        errtag=self.getTag('error')
        if errtag:
            for tag in errtag.getChildren():
                if tag.getName()<>'text': return tag.getName()
            return errtag.getData()
    def getErrorCode(self):
        """ Return the error code. Obsolette. """
        return self.getTagAttr('error','code')
    def setError(self,error,code=None):
        """ Set the error code. Obsolette. Use error-conditions instead. """
        if code:
            if str(code) in _errorcodes.keys(): error=ErrorNode(_errorcodes[str(code)],text=error)
            else: error=ErrorNode(ERR_UNDEFINED_CONDITION,code=code,typ='cancel',text=error)
        elif type(error) in [type(''),type(u'')]: error=ErrorNode(error)
        self.setType('error')
        self.addChild(node=error)
    def setTimestamp(self,val=None):
        """Set the timestamp. timestamp should be the yyyymmddThhmmss string."""
        if not val: val=time.strftime('%Y%m%dT%H:%M:%S', time.gmtime())
        self.timestamp=val
        self.setTag('x',{'stamp':self.timestamp},namespace=NS_DELAY)
    def getProperties(self):
        """ Return the list of namespaces to which belongs the direct childs of element"""
        props=[]
        for child in self.getChildren():
            prop=child.getNamespace()
            if prop not in props: props.append(prop)
        return props
    def __setitem__(self,item,val):
        """ Set the item 'item' to the value 'val'."""
        if item in ['to','from']: val=JID(val)
        return self.setAttr(item,val)

class Message(Protocol):
    """ XMPP Message stanza - "push" mechanism."""
    def __init__(self, to=None, body=None, typ=None, subject=None, attrs={}, frm=None, payload=[], timestamp=None, xmlns=NS_CLIENT, node=None):
        """ Create message object. You can specify recipient, text of message, type of message
            any additional attributes, sender of the message, any additional payload (f.e. jabber:x:delay element) and namespace in one go.
            Alternatively you can pass in the other XML object as the 'node' parameted to replicate it as message. """
        Protocol.__init__(self, 'message', to=to, typ=typ, attrs=attrs, frm=frm, payload=payload, timestamp=timestamp, xmlns=xmlns, node=node)
        if body: self.setBody(body)
        if subject: self.setSubject(subject)
    def getBody(self):
        """ Returns text of the message. """
        return self.getTagData('body')
    def getSubject(self):
        """ Returns subject of the message. """
        return self.getTagData('subject')
    def getThread(self):
        """ Returns thread of the message. """
        return self.getTagData('thread')
    def setBody(self,val):
        """ Sets the text of the message. """
        self.setTagData('body',val)
    def setSubject(self,val):
        """ Sets the subject of the message. """
        self.setTagData('subject',val)
    def setThread(self,val):
        """ Sets the thread of the message. """
        self.setTagData('thread',val)
    def buildReply(self,text=None):
        """ Builds and returns another message object with specified text.
            The to, from and thread properties of new message are pre-set as reply to this message. """
        m=Message(to=self.getFrom(),frm=self.getTo(),body=text)
        th=self.getThread()
        if th: m.setThread(th)
        return m

class Presence(Protocol):
    """ XMPP Presence object."""
    def __init__(self, to=None, typ=None, priority=None, show=None, status=None, attrs={}, frm=None, timestamp=None, payload=[], xmlns=NS_CLIENT, node=None):
        """ Create presence object. You can specify recipient, type of message, priority, show and status values
            any additional attributes, sender of the presence, timestamp, any additional payload (f.e. jabber:x:delay element) and namespace in one go.
            Alternatively you can pass in the other XML object as the 'node' parameted to replicate it as presence. """
        Protocol.__init__(self, 'presence', to=to, typ=typ, attrs=attrs, frm=frm, payload=payload, timestamp=timestamp, xmlns=xmlns, node=node)
        if priority: self.setPriority(priority)
        if show: self.setShow(show)
        if status: self.setStatus(status)
    def getPriority(self):
        """ Returns the priority of the message. """
        return self.getTagData('priority')
    def getShow(self):
        """ Returns the show value of the message. """
        return self.getTagData('show')
    def getStatus(self):
        """ Returns the status string of the message. """
        return self.getTagData('status')
    def setPriority(self,val):
        """ Sets the priority of the message. """
        self.setTagData('priority',val)
    def setShow(self,val):
        """ Sets the show value of the message. """
        self.setTagData('show',val)
    def setStatus(self,val):
        """ Sets the status string of the message. """
        self.setTagData('status',val)

    def _muc_getItemAttr(self,tag,attr):
        for xtag in self.getTags('x'):
            for child in xtag.getTags(tag):
                return child.getAttr(attr)
    def _muc_getSubTagDataAttr(self,tag,attr):
        for xtag in self.getTags('x'):
            for child in xtag.getTags('item'):
                for cchild in child.getTags(tag):
                    return cchild.getData(),cchild.getAttr(attr)
        return None,None
    def getRole(self):
        """Returns the presence role (for groupchat)"""
        return self._muc_getItemAttr('item','role')
    def getAffiliation(self):
        """Returns the presence affiliation (for groupchat)"""
        return self._muc_getItemAttr('item','affiliation')
    def getNick(self):
        """Returns the nick value (for nick change in groupchat)"""
        return self._muc_getItemAttr('item','nick')
    def getJid(self):
        """Returns the presence jid (for groupchat)"""
        return self._muc_getItemAttr('item','jid')
    def getReason(self):
        """Returns the reason of the presence (for groupchat)"""
        return self._muc_getSubTagDataAttr('reason','')[0]
    def getActor(self):
        """Returns the reason of the presence (for groupchat)"""
        return self._muc_getSubTagDataAttr('actor','jid')[1]
    def getStatusCode(self):
        """Returns the status code of the presence (for groupchat)"""
        return self._muc_getItemAttr('status','code')

class Iq(Protocol): 
    """ XMPP Iq object - get/set dialog mechanism. """
    def __init__(self, typ=None, queryNS=None, attrs={}, to=None, frm=None, payload=[], xmlns=NS_CLIENT, node=None):
        """ Create Iq object. You can specify type, query namespace
            any additional attributes, recipient of the iq, sender of the iq, any additional payload (f.e. jabber:x:data node) and namespace in one go.
            Alternatively you can pass in the other XML object as the 'node' parameted to replicate it as an iq. """
        Protocol.__init__(self, 'iq', to=to, typ=typ, attrs=attrs, frm=frm, xmlns=xmlns, node=node)
        if payload: self.setQueryPayload(payload)
        if queryNS: self.setQueryNS(queryNS)
    def getQueryNS(self):
        """ Return the namespace of the 'query' child element."""
        tag=self.getTag('query')
        if tag: return tag.getNamespace()
    def getQuerynode(self):
        """ Return the 'node' attribute value of the 'query' child element."""
        return self.getTagAttr('query','node')
    def getQueryPayload(self):
        """ Return the 'query' child element payload."""
        tag=self.getTag('query')
        if tag: return tag.getPayload()
    def getQueryChildren(self):
        """ Return the 'query' child element child nodes."""
        tag=self.getTag('query')
        if tag: return tag.getChildren()
    def setQueryNS(self,namespace):
        """ Set the namespace of the 'query' child element."""
        self.setTag('query').setNamespace(namespace)
    def setQueryPayload(self,payload):
        """ Set the 'query' child element payload."""
        self.setTag('query').setPayload(payload)
    def setQuerynode(self,node):
        """ Set the 'node' attribute value of the 'query' child element."""
        self.setTagAttr('query','node',node)
    def buildReply(self,typ):
        """ Builds and returns another Iq object of specified type.
            The to, from and query child node of new Iq are pre-set as reply to this Iq. """
        iq=Iq(typ,to=self.getFrom(),frm=self.getTo(),attrs={'id':self.getID()})
        if self.getTag('query'): iq.setQueryNS(self.getQueryNS())
        return iq

class ErrorNode(Node):
    """ XMPP-style error element.
        In the case of stanza error should be attached to XMPP stanza.
        In the case of stream-level errors should be used separately. """
    def __init__(self,name,code=None,typ=None,text=None):
        """ Create new error node object.
            Mandatory parameter: name - name of error condition.
            Optional parameters: code, typ, text. Used for backwards compartibility with older jabber protocol."""
        if ERRORS.has_key(name):
            cod,type,txt=ERRORS[name]
            ns=name.split()[0]
        else: cod,ns,type,txt='500',NS_STANZAS,'cancel',''
        if typ: type=typ
        if code: cod=code
        if text: txt=text
        Node.__init__(self,'error',{},[Node(name)])
        if type: self.setAttr('type',type)
        if not cod: self.setName('stream:error')
        if txt: self.addChild(node=Node(ns+' text',{},[txt]))
        if cod: self.setAttr('code',cod)

class Error(Protocol):
    """ Used to quickly transform received stanza into error reply."""
    def __init__(self,node,error,reply=1):
        """ Create error reply basing on the received 'node' stanza and the 'error' error condition.
            If the 'node' is not the received stanza but locally created ('to' and 'from' fields needs not swapping)
            specify the 'reply' argument as false."""
        if reply: Protocol.__init__(self,to=node.getFrom(),frm=node.getTo(),node=node)
        else: Protocol.__init__(self,node=node)
        self.setError(error)
        if node.getType()=='error': self.__str__=self.__dupstr__
    def __dupstr__(self,dup1=None,dup2=None):
        """ Dummy function used as preventor of creating error node in reply to error node.
            I.e. you will not be able to serialise "double" error into string.
        """
        return ''

class DataField(Node):
    """ This class is used in the DataForm class to describe the single data item.
        If you are working with jabber:x:data (XEP-0004, XEP-0068, XEP-0122) 
        then you will need to work with instances of this class. """
    def __init__(self,name=None,value=None,typ=None,required=0,label=None,desc=None,options=[],node=None):
        """ Create new data field of specified name,value and type.
            Also 'required','desc' and 'options' fields can be set.
            Alternatively other XML object can be passed in as the 'node' parameted to replicate it as a new datafiled.
            """
        Node.__init__(self,'field',node=node)
        if name: self.setVar(name)
        if type(value) in [list,tuple]: self.setValues(value)
        elif value: self.setValue(value)
        if typ: self.setType(typ)
        elif not typ and not node: self.setType('text-single')
        if required: self.setRequired(required)
        if label: self.setLabel(label)
        if desc: self.setDesc(desc)
        if options: self.setOptions(options)
    def setRequired(self,req=1):
        """ Change the state of the 'required' flag. """
        if req: self.setTag('required')
        else:
            try: self.delChild('required')
            except ValueError: return
    def isRequired(self):
        """ Returns in this field a required one. """
        return self.getTag('required')
    def setLabel(self,label):
        """ Set the label of this field. """
        self.setAttr('label',label)
    def getLabel(self):
        """ Return the label of this field. """
        return self.getAttr('label')
    def setDesc(self,desc):
        """ Set the description of this field. """
        self.setTagData('desc',desc)
    def getDesc(self):
        """ Return the description of this field. """
        return self.getTagData('desc')
    def setValue(self,val):
        """ Set the value of this field. """
        self.setTagData('value',val)
    def getValue(self):
        return self.getTagData('value')
    def setValues(self,lst):
        """ Set the values of this field as values-list.
            Replaces all previous filed values! If you need to just add a value - use addValue method."""
        while self.getTag('value'): self.delChild('value')
        for val in lst: self.addValue(val)
    def addValue(self,val):
        """ Add one more value to this field. Used in 'get' iq's or such."""
        self.addChild('value',{},[val])
    def getValues(self):
        """ Return the list of values associated with this field."""
        ret=[]
        for tag in self.getTags('value'): ret.append(tag.getData())
        return ret
    def getOptions(self):
        """ Return label-option pairs list associated with this field."""
        ret=[]
        for tag in self.getTags('option'): ret.append([tag.getAttr('label'),tag.getTagData('value')])
        return ret
    def setOptions(self,lst):
        """ Set label-option pairs list associated with this field."""
        while self.getTag('option'): self.delChild('option')
        for opt in lst: self.addOption(opt)
    def addOption(self,opt):
        """ Add one more label-option pair to this field."""
        if type(opt) in [str,unicode]: self.addChild('option').setTagData('value',opt)
        else: self.addChild('option',{'label':opt[0]}).setTagData('value',opt[1])
    def getType(self):
        """ Get type of this field. """
        return self.getAttr('type')
    def setType(self,val):
        """ Set type of this field. """
        return self.setAttr('type',val)
    def getVar(self):
        """ Get 'var' attribute value of this field. """
        return self.getAttr('var')
    def setVar(self,val):
        """ Set 'var' attribute value of this field. """
        return self.setAttr('var',val)

class DataReported(Node):
    """ This class is used in the DataForm class to describe the 'reported data field' data items which are used in
        'multiple item form results' (as described in XEP-0004).
        Represents the fields that will be returned from a search. This information is useful when
        you try to use the jabber:iq:search namespace to return dynamic form information.
        """
    def __init__(self,node=None):
        """ Create new empty 'reported data' field. However, note that, according XEP-0004:
            * It MUST contain one or more DataFields.
            * Contained DataFields SHOULD possess a 'type' and 'label' attribute in addition to 'var' attribute
            * Contained DataFields SHOULD NOT contain a <value/> element.
            Alternatively other XML object can be passed in as the 'node' parameted to replicate it as a new
            dataitem.
        """
        Node.__init__(self,'reported',node=node)
        if node:
            newkids=[]
            for n in self.getChildren():
                if    n.getName()=='field': newkids.append(DataField(node=n))
                else: newkids.append(n)
            self.kids=newkids
    def getField(self,name):
        """ Return the datafield object with name 'name' (if exists). """
        return self.getTag('field',attrs={'var':name})
    def setField(self,name,typ=None,label=None):
        """ Create if nessessary or get the existing datafield object with name 'name' and return it.
            If created, attributes 'type' and 'label' are applied to new datafield."""
        f=self.getField(name)
        if f: return f
        return self.addChild(node=DataField(name,None,typ,0,label))
    def asDict(self):
        """ Represent dataitem as simple dictionary mapping of datafield names to their values."""
        ret={}
        for field in self.getTags('field'):
            name=field.getAttr('var')
            typ=field.getType()
            if isinstance(typ,(str,unicode)) and typ[-6:]=='-multi':
                val=[]
                for i in field.getTags('value'): val.append(i.getData())
            else: val=field.getTagData('value')
            ret[name]=val
        if self.getTag('instructions'): ret['instructions']=self.getInstructions()
        return ret
    def __getitem__(self,name):
        """ Simple dictionary interface for getting datafields values by their names."""
        item=self.getField(name)
        if item: return item.getValue()
        raise IndexError('No such field')
    def __setitem__(self,name,val):
        """ Simple dictionary interface for setting datafields values by their names."""
        return self.setField(name).setValue(val)

class DataItem(Node):
    """ This class is used in the DataForm class to describe data items which are used in 'multiple
        item form results' (as described in XEP-0004).
        """
    def __init__(self,node=None):
        """ Create new empty data item. However, note that, according XEP-0004, DataItem MUST contain ALL
            DataFields described in DataReported.
            Alternatively other XML object can be passed in as the 'node' parameted to replicate it as a new
            dataitem.
            """
        Node.__init__(self,'item',node=node)
        if node:
            newkids=[]
            for n in self.getChildren():
                if    n.getName()=='field': newkids.append(DataField(node=n))
                else: newkids.append(n)
            self.kids=newkids
    def getField(self,name):
        """ Return the datafield object with name 'name' (if exists). """
        return self.getTag('field',attrs={'var':name})
    def setField(self,name):
        """ Create if nessessary or get the existing datafield object with name 'name' and return it. """
        f=self.getField(name)
        if f: return f
        return self.addChild(node=DataField(name))
    def asDict(self):
        """ Represent dataitem as simple dictionary mapping of datafield names to their values."""
        ret={}
        for field in self.getTags('field'):
            name=field.getAttr('var')
            typ=field.getType()
            if isinstance(typ,(str,unicode)) and typ[-6:]=='-multi':
                val=[]
                for i in field.getTags('value'): val.append(i.getData())
            else: val=field.getTagData('value')
            ret[name]=val
        if self.getTag('instructions'): ret['instructions']=self.getInstructions()
        return ret
    def __getitem__(self,name):
        """ Simple dictionary interface for getting datafields values by their names."""
        item=self.getField(name)
        if item: return item.getValue()
        raise IndexError('No such field')
    def __setitem__(self,name,val):
        """ Simple dictionary interface for setting datafields values by their names."""
        return self.setField(name).setValue(val)

class DataForm(Node):
    """ DataForm class. Used for manipulating dataforms in XMPP.
        Relevant XEPs: 0004, 0068, 0122.
        Can be used in disco, pub-sub and many other applications."""
    def __init__(self, typ=None, data=[], title=None, node=None):
        """
            Create new dataform of type 'typ'; 'data' is the list of DataReported,
            DataItem and DataField instances that this dataform contains; 'title'
            is the title string.
            You can specify the 'node' argument as the other node to be used as
            base for constructing this dataform.

            title and instructions is optional and SHOULD NOT contain newlines.
            Several instructions MAY be present.
            'typ' can be one of ('form' | 'submit' | 'cancel' | 'result' )
            'typ' of reply iq can be ( 'result' | 'set' | 'set' | 'result' ) respectively.
            'cancel' form can not contain any fields. All other forms contains AT LEAST one field.
            'title' MAY be included in forms of type "form" and "result"
        """
        Node.__init__(self,'x',node=node)
        if node:
            newkids=[]
            for n in self.getChildren():
                if   n.getName()=='field': newkids.append(DataField(node=n))
                elif n.getName()=='item': newkids.append(DataItem(node=n))
                elif n.getName()=='reported': newkids.append(DataReported(node=n))
                else: newkids.append(n)
            self.kids=newkids
        if typ: self.setType(typ)
        self.setNamespace(NS_DATA)
        if title: self.setTitle(title)
        if type(data)==type({}):
            newdata=[]
            for name in data.keys(): newdata.append(DataField(name,data[name]))
            data=newdata
        for child in data:
            if type(child) in [type(''),type(u'')]: self.addInstructions(child)
            elif child.__class__.__name__=='DataField': self.kids.append(child)
            elif child.__class__.__name__=='DataItem': self.kids.append(child)
            elif child.__class__.__name__=='DataReported': self.kids.append(child)
            else: self.kids.append(DataField(node=child))
    def getType(self):
        """ Return the type of dataform. """
        return self.getAttr('type')
    def setType(self,typ):
        """ Set the type of dataform. """
        self.setAttr('type',typ)
    def getTitle(self):
        """ Return the title of dataform. """
        return self.getTagData('title')
    def setTitle(self,text):
        """ Set the title of dataform. """
        self.setTagData('title',text)
    def getInstructions(self):
        """ Return the instructions of dataform. """
        return self.getTagData('instructions')
    def setInstructions(self,text):
        """ Set the instructions of dataform. """
        self.setTagData('instructions',text)
    def addInstructions(self,text):
        """ Add one more instruction to the dataform. """
        self.addChild('instructions',{},[text])
    def getField(self,name):
        """ Return the datafield object with name 'name' (if exists). """
        return self.getTag('field',attrs={'var':name})
    def setField(self,name):
        """ Create if nessessary or get the existing datafield object with name 'name' and return it. """
        f=self.getField(name)
        if f: return f
        return self.addChild(node=DataField(name))
    def asDict(self):
        """ Represent dataform as simple dictionary mapping of datafield names to their values."""
        ret={}
        for field in self.getTags('field'):
            name=field.getAttr('var')
            typ=field.getType()
            if isinstance(typ,(str,unicode)) and typ[-6:]=='-multi':
                val=[]
                for i in field.getTags('value'): val.append(i.getData())
            else: val=field.getTagData('value')
            ret[name]=val
        if self.getTag('instructions'): ret['instructions']=self.getInstructions()
        return ret
    def __getitem__(self,name):
        """ Simple dictionary interface for getting datafields values by their names."""
        item=self.getField(name)
        if item: return item.getValue()
        raise IndexError('No such field')
    def __setitem__(self,name,val):
        """ Simple dictionary interface for setting datafields values by their names."""
        return self.setField(name).setValue(val)
