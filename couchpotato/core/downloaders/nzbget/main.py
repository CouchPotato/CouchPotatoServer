from base64 import standard_b64encode
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.logger import CPLog
from inspect import isfunction
import socket
import traceback
import xmlrpclib

log = CPLog(__name__)

class NZBGet(Downloader):

    type = ['nzb']

    url = 'http://nzbget:%(password)s@%(host)s/xmlrpc'

    def download(self, data = {}, movie = {}):

        if self.isDisabled() or not self.isCorrectType(data.get('type')):
            return

        log.info('Sending "%s" to NZBGet.' % data.get('name'))

        url = self.url % {'host': self.conf('host'), 'password': self.conf('password')}
        nzb_name = data.get('name') + '.nzb'

        rpc = xmlrpclib.ServerProxy(url)
        try:
            if rpc.writelog('INFO', 'CouchPotato connected to drop off %s.' % nzb_name):
                log.info('Successfully connected to NZBGet')
            else:
                log.info('Successfully connected to NZBGet, but unable to send a message')
        except socket.error:
            log.error('NZBGet is not responding. Please ensure that NZBGet is running and host setting is correct.')
            return False
        except xmlrpclib.ProtocolError, e:
            if e.errcode == 401:
                log.error('Password is incorrect.')
            else:
                log.error('Protocol Error: %s' % e)
            return False

        try:
            if isfunction(data.get('download')):
                filedata = data.get('download')()
                if not filedata:
                    log.error('Failed download file: %s' % nzb_name)
                    return False
            else:
                log.info('Downloading: %s' % data.get('url'))
                filedata = self.urlopen(data.get('url'))
        except:
            log.error('Unable to get NZB file: %s' % traceback.format_exc())
            return False

        if rpc.append(nzb_name, self.conf('category'), False, standard_b64encode(filedata.strip())):
            log.info('NZB sent successfully to NZBGet')
            return True
        else:
            log.error('NZBGet could not add %s to the queue.' % nzb_name)
            return False
