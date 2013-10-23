"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.features.feature_session.session import FeatureSession
from sleekxmpp.features.feature_session.stanza import Session


register_plugin(FeatureSession)


# Retain some backwards compatibility
feature_session = FeatureSession
