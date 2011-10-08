# Based on netprowl by the following authors.

# Altered 1st October 2010 - Tim Child.
# Have added the ability for the command line arguments to take a password.

# Altered 1-17-2010 - Tanner Stokes - www.tannr.com
# Added support for command line arguments

# ORIGINAL CREDITS
# """Growl 0.6 Network Protocol Client for Python"""
# __version__ = "0.6.3"
# __author__ = "Rui Carmo (http://the.taoofmac.com)"
# __copyright__ = "(C) 2004 Rui Carmo. Code under BSD License."
# __contributors__ = "Ingmar J Stein (Growl Team), John Morrissey (hashlib patch)"

import struct

try:
    import hashlib
    md5_constructor = hashlib.md5
except ImportError:
    import md5
    md5_constructor = md5.new

GROWL_UDP_PORT = 9887
GROWL_PROTOCOL_VERSION = 1
GROWL_TYPE_REGISTRATION = 0
GROWL_TYPE_NOTIFICATION = 1


class GrowlRegistrationPacket:
    """Builds a Growl Network Registration packet.
    Defaults to emulating the command-line growlnotify utility."""

    def __init__(self, application = "CouchPotato", password = None):
        self.notifications = []
        self.defaults = [] # array of indexes into notifications
        self.application = application.encode("utf-8")
        self.password = password

    def addNotification(self, notification = "General Notification", enabled = True):
        """Adds a notification type and sets whether it is enabled on the GUI"""

        self.notifications.append(notification)
        if enabled:
            self.defaults.append(len(self.notifications) - 1)

    def payload(self):
        """Returns the packet payload."""
        self.data = struct.pack("!BBH",
            GROWL_PROTOCOL_VERSION,
            GROWL_TYPE_REGISTRATION,
            len(self.application)
        )
        self.data += struct.pack("BB",
            len(self.notifications),
            len(self.defaults)
        )
        self.data += self.application
        for notification in self.notifications:
            encoded = notification.encode("utf-8")
            self.data += struct.pack("!H", len(encoded))
            self.data += encoded
        for default in self.defaults:
            self.data += struct.pack("B", default)
        self.checksum = md5_constructor()
        self.checksum.update(self.data)
        if self.password:
            self.checksum.update(self.password)
        self.data += self.checksum.digest()
        return self.data

class GrowlNotificationPacket:
    """Builds a Growl Network Notification packet.
    Defaults to emulating the command-line growlnotify utility."""

    def __init__(self, application = "CouchPotato",
                             notification = "General Notification", title = "Title",
                             description = "Description", priority = 0, sticky = False, password = None):

        self.application = application.encode("utf-8")
        self.notification = notification.encode("utf-8")
        self.title = title.encode("utf-8")
        self.description = description.encode("utf-8")
        flags = (priority & 0x07) * 2
        if priority < 0:
            flags |= 0x08
        if sticky:
            flags = flags | 0x0100
        self.data = struct.pack("!BBHHHHH",
            GROWL_PROTOCOL_VERSION,
            GROWL_TYPE_NOTIFICATION,
            flags,
            len(self.notification),
            len(self.title),
            len(self.description),
            len(self.application)
        )
        self.data += self.notification
        self.data += self.title
        self.data += self.description
        self.data += self.application
        self.checksum = md5_constructor()
        self.checksum.update(self.data)
        if password:
            self.checksum.update(password)
        self.data += self.checksum.digest()

    def payload(self):
        """Returns the packet payload."""
        return self.data
