"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


from sleekxmpp.plugins import BasePlugin, register_plugin


class XEP_0133(BasePlugin):

    name = 'xep_0133'
    description = 'XEP-0133: Service Administration'
    dependencies = set(['xep_0030', 'xep_0004', 'xep_0050'])
    commands = set(['add-user', 'delete-user', 'disable-user',
                    'reenable-user', 'end-user-session', 'get-user-password',
                    'change-user-password', 'get-user-roster',
                    'get-user-lastlogin', 'user-stats', 'edit-blacklist',
                    'edit-whitelist', 'get-registered-users-num',
                    'get-disabled-users-num', 'get-online-users-num',
                    'get-active-users-num', 'get-idle-users-num',
                    'get-registered-users-list', 'get-disabled-users-list',
                    'get-online-users-list', 'get-online-users',
                    'get-active-users', 'get-idle-userslist', 'announce',
                    'set-motd', 'edit-motd', 'delete-motd', 'set-welcome',
                    'delete-welcome', 'edit-admin', 'restart', 'shutdown'])

    def get_commands(self, jid=None, **kwargs):
        if jid is None:
            jid = self.xmpp.boundjid.server
        return self.xmpp['xep_0050'].get_commands(jid, **kwargs)


def create_command(name):
    def admin_command(self, jid=None, session=None, ifrom=None, block=False):
        if jid is None:
            jid = self.xmpp.boundjid.server
        self.xmpp['xep_0050'].start_command(
                jid=jid,
                node='http://jabber.org/protocol/admin#%s' % name,
                session=session,
                ifrom=ifrom,
                block=block)
    return admin_command


for cmd in XEP_0133.commands:
    setattr(XEP_0133, cmd.replace('-', '_'), create_command(cmd))


register_plugin(XEP_0133)
