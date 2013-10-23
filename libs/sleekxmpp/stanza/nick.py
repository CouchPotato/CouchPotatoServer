"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

# The nickname stanza has been moved to its own plugin, but the existing
# references are kept for backwards compatibility.

from sleekxmpp.stanza import Message, Presence
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0172 import UserNick as Nick

register_stanza_plugin(Message, Nick)
register_stanza_plugin(Presence, Nick)

# To comply with PEP8, method names now use underscores.
# Deprecated method names are re-mapped for backwards compatibility.
Nick.setNick = Nick.set_nick
Nick.getNick = Nick.get_nick
Nick.delNick = Nick.del_nick
