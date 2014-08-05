import re
import telnetlib

from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = CPLog(__name__)

autoload = 'NMJ'


class NMJ(Notification):

    # noinspection PyMissingConstructor
    def __init__(self):
        addApiView(self.testNotifyName(), self.test)
        addApiView('notify.nmj.auto_config', self.autoConfig)

        addEvent('renamer.after', self.addToLibrary)

    def autoConfig(self, host = 'localhost', **kwargs):

        mount = ''

        try:
            terminal = telnetlib.Telnet(host)
        except Exception:
            log.error('Warning: unable to get a telnet session to %s', host)
            return self.failed()

        log.debug('Connected to %s via telnet', host)
        terminal.read_until('sh-3.00# ')
        terminal.write('cat /tmp/source\n')
        terminal.write('cat /tmp/netshare\n')
        terminal.write('exit\n')
        tnoutput = terminal.read_all()

        match = re.search(r'(.+\.db)\r\n?(.+)(?=sh-3.00# cat /tmp/netshare)', tnoutput)

        if match:
            database = match.group(1)
            device = match.group(2)
            log.info('Found NMJ database %s on device %s', (database, device))
        else:
            log.error('Could not get current NMJ database on %s, NMJ is probably not running!', host)
            return self.failed()

        if device.startswith('NETWORK_SHARE/'):
            match = re.search('.*(?=\r\n?%s)' % (re.escape(device[14:])), tnoutput)

            if match:
                mount = match.group().replace('127.0.0.1', host)
                log.info('Found mounting url on the Popcorn Hour in configuration: %s', mount)
            else:
                log.error('Detected a network share on the Popcorn Hour, but could not get the mounting url')
                return self.failed()

        return {
            'success': True,
            'database': database,
            'mount': mount,
        }

    def addToLibrary(self, message = None, group = None):
        if self.isDisabled(): return
        if not group: group = {}

        host = self.conf('host')
        mount = self.conf('mount')
        database = self.conf('database')

        if mount:
            log.debug('Try to mount network drive via url: %s', mount)
            try:
                self.urlopen(mount)
            except:
                return False

        params = {
            'arg0': 'scanner_start',
            'arg1': database,
            'arg2': 'background',
            'arg3': '',
        }
        params = tryUrlencode(params)
        update_url = 'http://%(host)s:8008/metadata_database?%(params)s' % {'host': host, 'params': params}

        try:
            response = self.urlopen(update_url)
        except:
            return False

        try:
            et = etree.fromstring(response)
            result = et.findtext('returnValue')
        except SyntaxError as e:
            log.error('Unable to parse XML returned from the Popcorn Hour: %s', e)
            return False

        if int(result) > 0:
            log.error('Popcorn Hour returned an errorcode: %s', result)
            return False
        else:
            log.info('NMJ started background scan')
            return True

    def failed(self):
        return {
            'success': False
        }

    def test(self, **kwargs):
        return {
            'success': self.addToLibrary()
        }


config = [{
    'name': 'nmj',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'nmj',
            'label': 'NMJ',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost',
                },
                {
                    'name': 'database',
                },
                {
                    'name': 'mount',
                },
            ],
        }
    ],
}]
