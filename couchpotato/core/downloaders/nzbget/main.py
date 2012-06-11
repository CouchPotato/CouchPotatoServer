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

    def download(self, data = {}, movie = {}, manual = False, filedata = None):

        if self.isDisabled(manual) or not self.isCorrectType(data.get('type')):
            return

        if not filedata:
            log.error('Unable to get NZB file: %s', traceback.format_exc())
            return False

        log.info('Sending "%s" to NZBGet.', data.get('name'))

        url = self.url % {'host': self.conf('host'), 'password': self.conf('password')}
        nzb_name = '%s.nzb' % self.createNzbName(data, movie)

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
                log.error('Protocol Error: %s', e)
            return False

        if rpc.append(nzb_name, self.conf('category'), False, standard_b64encode(filedata.strip())):
            log.info('NZB sent successfully to NZBGet')
            return True
        else:
            log.error('NZBGet could not add %s to the queue.', nzb_name)
            return False
