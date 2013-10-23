"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.features.feature_preapproval.preapproval import FeaturePreApproval
from sleekxmpp.features.feature_preapproval.stanza import PreApproval


register_plugin(FeaturePreApproval)
