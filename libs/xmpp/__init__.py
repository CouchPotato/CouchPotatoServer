# $Id: __init__.py,v 1.9 2005/03/07 09:34:51 snakeru Exp $

"""
All features of xmpppy library contained within separate modules.
At present there are modules:
simplexml - XML handling routines
protocol - jabber-objects (I.e. JID and different stanzas and sub-stanzas) handling routines.
debug - Jacob Lundquist's debugging module. Very handy if you like colored debug.
auth - Non-SASL and SASL stuff. You will need it to auth as a client or transport.
transports - low level connection handling. TCP and TLS currently. HTTP support planned.
roster - simple roster for use in clients.
dispatcher - decision-making logic. Handles all hooks. The first who takes control over fresh stanzas.
features - different stuff that didn't worths separating into modules
browser - DISCO server framework. Allows to build dynamic disco tree.
filetransfer - Currently contains only IBB stuff. Can be used for bot-to-bot transfers.

Most of the classes that is defined in all these modules is an ancestors of 
class PlugIn so they share a single set of methods allowing you to compile 
a featured XMPP client. For every instance of PlugIn class the 'owner' is the class
in what the plug was plugged. While plugging in such instance usually sets some
methods of owner to it's own ones for easy access. All session specific info stored
either in instance of PlugIn or in owner's instance. This is considered unhandy
and there are plans to port 'Session' class from xmppd.py project for storing all
session-related info. Though if you are not accessing instances variables directly
and use only methods for access all values you should not have any problems.

"""

import simplexml,protocol,debug,auth,transports,roster,dispatcher,features,browser,filetransfer,commands
from client import *
from protocol import *
