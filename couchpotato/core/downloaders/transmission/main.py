#!/usr/bin/python
# -*- coding: utf-8 -*-

from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
import urllib2
import httplib
import json
import re
log = CPLog(__name__)


class TransmissionRPC(object):

    """TransmissionRPC lite library"""

    def __init__(
        self,
        host='localhost',
        port=9091,
        username=None,
        password=None,
        ):

        super(TransmissionRPC, self).__init__()
        self.url = 'http://' + host + ':' + str(port) \
            + '/transmission/rpc'
        self.tag = 0
        self.session_id = 0
        self.session = {}
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm=None, uri=self.url,
                    user=username, passwd=password)
            opener = \
                urllib2.build_opener(urllib2.HTTPBasicAuthHandler(password_manager),
                    urllib2.HTTPDigestAuthHandler(password_manager))
            opener.addheaders = [('User-agent',
                                 'couchpotato-transmission-client/1.0')]
            urllib2.install_opener(opener)
        elif username or password:
            log.debug('User or password missing, not using authentication.'
                      )
        self.session = self.get_session()

    def _request(self, ojson):
        self.tag += 1
        headers = {'x-transmission-session-id': str(self.session_id)}
        request = urllib2.Request(self.url,
                                  json.dumps(ojson).encode('utf-8'),
                                  headers)
        try:
            open_request = urllib2.urlopen(request)
            response = json.loads(open_request.read())
            log.debug('response: '
                      + str(json.dumps(response).encode('utf-8')))
            if response['result'] == 'success':
                log.debug(u'Transmission action successfull')
                return response['arguments']
            else:
                log.debug('Unknown failure sending command to Transmission. Return text is: '
                           + response['result'])
                return False
        except httplib.InvalidURL, e:
            log.error(u'Invalid Transmission host, check your config %s'
                       % e)
            return False
        except urllib2.HTTPError, e:
            if e.code == 401:
                log.error(u'Invalid Transmission Username or Password, check your config'
                          )
                return False
            elif e.code == 409:
                msg = str(e.read())
                try:
                    self.session_id = \
                        re.search('X-Transmission-Session-Id:\s*(\w+)',
                                  msg).group(1)
                    log.debug('X-Transmission-Session-Id: '
                              + self.session_id)

                    # #resend request with the updated header

                    return self._request(ojson)
                except:
                    log.error(u'Unable to get Transmission Session-Id %s'
                               % e)
            else:
                log.error(u'TransmissionRPC HTTPError: %s' % e)
        except urllib2.URLError, e:
            log.error(u'Unable to connect to Transmission %s' % e)

    def get_session(self):
        post_data = {'method': 'session-get', 'tag': self.tag}
        return self._request(post_data)

    def add_torrent_uri(self, torrent, arguments={}):
        arguments['filename'] = torrent
        post_data = {'arguments': arguments, 'method': 'torrent-add',
                     'tag': self.tag}
        return self._request(post_data)

    def add_torrent_file(self, torrent, arguments={}):
        arguments['metainfo'] = torrent
        post_data = {'arguments': arguments, 'method': 'torrent-add',
                     'tag': self.tag}
        return self._request(post_data)

    def set_torrent(self, id, arguments={}):
        arguments['ids'] = id
        post_data = {'arguments': arguments, 'method': 'torrent-set',
                     'tag': self.tag}
        return self._request(post_data)


class Transmission(Downloader):

    type = ['torrent', 'magnet']

    def download(
        self,
        data={},
        movie={},
        manual=False,
        filedata=None,
        ):

        print data
        if self.isDisabled(manual) \
            or not self.isCorrectType(data.get('type')):
            return

        log.debug('Sending "%s" to Transmission.', data.get('name'))
        log.debug('Type "%s" to Transmission.', data.get('type'))

        # Load host from config and split out port.

        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.'
                      )
            return False

        # Set parameters for Transmission

        params = {'paused': self.conf('paused', default=0),
                  'download-dir': self.conf('directory', default=None)}

        torrent_params = {'seedRatioLimit': self.conf('ratio'),
                          'seedRatioMode': (0 if self.conf('ratio'
                          ) else 1)}

        if not filedata or data.get('type') != 'magnet':
            log.error('Failed sending torrent, no data')

        # Send request to Transmission

        try:
            tc = TransmissionRPC(host[0], port=host[1],
                                 username=self.conf('username'),
                                 password=self.conf('password'))
            if data.get('type') == 'magnet' or data.get('magnet') != None:
                remote_torrent = tc.add_torrent_uri(data.get('magnet'), arguments=params)
            else:
                remote_torrent = tc.add_torrent_file(b64encode(filedata), arguments=params)

            # Change settings of added torrents
            print remote_torrent
            tc.set_torrent(remote_torrent['torrent-added']['hashString'
                           ], torrent_params)
            return True
        except Exception, e:
            log.error('Failed to change settings for transfer: %s', e)
            return False
