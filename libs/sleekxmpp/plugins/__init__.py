"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import PluginManager, PluginNotFound, BasePlugin
from sleekxmpp.plugins.base import register_plugin, load_plugin


__all__ = [
    # Non-standard
    'gmail_notify',  # Gmail searching and notifications

    # XEPS
    'xep_0004',  # Data Forms
    'xep_0009',  # Jabber-RPC
    'xep_0012',  # Last Activity
    'xep_0013',  # Flexible Offline Message Retrieval
    'xep_0016',  # Privacy Lists
    'xep_0027',  # Current Jabber OpenPGP Usage
    'xep_0030',  # Service Discovery
    'xep_0033',  # Extended Stanza Addresses
    'xep_0045',  # Multi-User Chat (Client)
    'xep_0047',  # In-Band Bytestreams
    'xep_0049',  # Private XML Storage
    'xep_0050',  # Ad-hoc Commands
    'xep_0054',  # vcard-temp
    'xep_0059',  # Result Set Management
    'xep_0060',  # Pubsub (Client)
    'xep_0066',  # Out of Band Data
    'xep_0077',  # In-Band Registration
#   'xep_0078',  # Non-SASL auth. Don't automatically load
    'xep_0080',  # User Location
    'xep_0082',  # XMPP Date and Time Profiles
    'xep_0084',  # User Avatar
    'xep_0085',  # Chat State Notifications
    'xep_0086',  # Legacy Error Codes
    'xep_0091',  # Legacy Delayed Delivery
    'xep_0092',  # Software Version
    'xep_0106',  # JID Escaping
    'xep_0107',  # User Mood
    'xep_0108',  # User Activity
    'xep_0115',  # Entity Capabilities
    'xep_0118',  # User Tune
    'xep_0128',  # Extended Service Discovery
    'xep_0131',  # Standard Headers and Internet Metadata
    'xep_0133',  # Service Administration
    'xep_0153',  # vCard-Based Avatars
    'xep_0163',  # Personal Eventing Protocol
    'xep_0172',  # User Nickname
    'xep_0184',  # Message Receipts
    'xep_0186',  # Invisible Command
    'xep_0191',  # Blocking Command
    'xep_0198',  # Stream Management
    'xep_0199',  # Ping
    'xep_0202',  # Entity Time
    'xep_0203',  # Delayed Delivery
    'xep_0221',  # Data Forms Media Element
    'xep_0222',  # Persistent Storage of Public Data via Pubsub
    'xep_0223',  # Persistent Storage of Private Data via Pubsub
    'xep_0224',  # Attention
    'xep_0231',  # Bits of Binary
    'xep_0235',  # OAuth Over XMPP
    'xep_0242',  # XMPP Client Compliance 2009
    'xep_0249',  # Direct MUC Invitations
    'xep_0256',  # Last Activity in Presence
    'xep_0257',  # Client Certificate Management for SASL EXTERNAL
    'xep_0258',  # Security Labels in XMPP
    'xep_0270',  # XMPP Compliance Suites 2010
    'xep_0279',  # Server IP Check
    'xep_0280',  # Message Carbons
    'xep_0297',  # Stanza Forwarding
    'xep_0302',  # XMPP Compliance Suites 2012
    'xep_0308',  # Last Message Correction
    'xep_0313',  # Message Archive Management
]
