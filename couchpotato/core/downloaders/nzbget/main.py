from base64 import standard_b64encode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.variable import tryInt, md5
from couchpotato.core.logger import CPLog
from datetime import timedelta
import re
import shutil
import socket
import traceback
import xmlrpclib

log = CPLog(__name__)

class NZBGet(Downloader):

    type = ['nzb']

    url = 'http://%(username)s:%(password)s@%(host)s/xmlrpc'

    def download(self, data = {}, movie = {}, filedata = None):

        if not filedata:
            log.error('Unable to get NZB file: %s', traceback.format_exc())
            return False

        log.info('Sending "%s" to NZBGet.', data.get('name'))

        url = self.url % {'host': self.conf('host'), 'username': self.conf('username'), 'password': self.conf('password')}
        nzb_name = ss('%s.nzb' % self.createNzbName(data, movie))

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

        if re.search(r"^0", rpc.version()):
            xml_response = rpc.append(nzb_name, self.conf('category'), False, standard_b64encode(filedata.strip()))
        else:
            xml_response = rpc.append(nzb_name, self.conf('category'), tryInt(self.conf('priority')), False, standard_b64encode(filedata.strip()))

        if xml_response:
            log.info('NZB sent successfully to NZBGet')
            nzb_id = md5(data['url']) # about as unique as they come ;)
            couchpotato_id = "couchpotato=" + nzb_id
            groups = rpc.listgroups()
            file_id = [item['LastID'] for item in groups if item['NZBFilename'] == nzb_name]
            confirmed = rpc.editqueue("GroupSetParameter", 0, couchpotato_id, file_id)
            if confirmed:
                log.debug('couchpotato parameter set in nzbget download')
            return self.downloadReturnId(nzb_id)
        else:
            log.error('NZBGet could not add %s to the queue.', nzb_name)
            return False

    def getAllDownloadStatus(self):

        log.debug('Checking NZBGet download status.')

        url = self.url % {'host': self.conf('host'), 'username': self.conf('username'), 'password': self.conf('password')}

        rpc = xmlrpclib.ServerProxy(url)
        try:
            if rpc.writelog('INFO', 'CouchPotato connected to check status'):
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

        # Get NZBGet data
        try:
            status = rpc.status()
            groups = rpc.listgroups()
            queue = rpc.postqueue(0)
            history = rpc.history()
        except:
            log.error('Failed getting data: %s', traceback.format_exc(1))
            return False

        statuses = StatusList(self)

        for item in groups:
            log.debug('Found %s in NZBGet download queue', item['NZBFilename'])
            try:
                nzb_id = [param['Value'] for param in item['Parameters'] if param['Name'] == 'couchpotato'][0]
            except:
                nzb_id = item['NZBID']
            statuses.append({
                'id': nzb_id,
                'name': item['NZBFilename'],
                'original_status': 'DOWNLOADING' if item['ActiveDownloads'] > 0 else 'QUEUED',
                # Seems to have no native API function for time left. This will return the time left after NZBGet started downloading this item
                'timeleft': str(timedelta(seconds = item['RemainingSizeMB'] / status['DownloadRate'] * 2 ^ 20)) if item['ActiveDownloads'] > 0 and not (status['DownloadPaused'] or status['Download2Paused']) else -1,
            })

        for item in queue: # 'Parameters' is not passed in rpc.postqueue
            log.debug('Found %s in NZBGet postprocessing queue', item['NZBFilename'])
            statuses.append({
                'id': item['NZBID'],
                'name': item['NZBFilename'],
                'original_status': item['Stage'],
                'timeleft': str(timedelta(seconds = 0)) if not status['PostPaused'] else -1,
            })

        for item in history:
            log.debug('Found %s in NZBGet history. ParStatus: %s, ScriptStatus: %s, Log: %s', (item['NZBFilename'] , item['ParStatus'], item['ScriptStatus'] , item['Log']))
            try:
                nzb_id = [param['Value'] for param in item['Parameters'] if param['Name'] == 'couchpotato'][0]
            except:
                nzb_id = item['NZBID']
            statuses.append({
                'id': nzb_id,
                'name': item['NZBFilename'],
                'status': 'completed' if item['ParStatus'] == 'SUCCESS' and item['ScriptStatus'] == 'SUCCESS' else 'failed',
                'original_status': item['ParStatus'] + ', ' + item['ScriptStatus'],
                'timeleft': str(timedelta(seconds = 0)),
                'folder': item['DestDir']
            })

        return statuses

    def removeFailed(self, item):

        log.info('%s failed downloading, deleting...', item['name'])

        url = self.url % {'host': self.conf('host'), 'password': self.conf('password')}

        rpc = xmlrpclib.ServerProxy(url)
        try:
            if rpc.writelog('INFO', 'CouchPotato connected to delete some history'):
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

        try:
            history = rpc.history()
            for hist in history:
                if hist['Parameters'] and hist['Parameters']['couchpotato'] and hist['Parameters']['couchpotato'] == item['id']:
                    nzb_id = hist['ID']
                    path = hist['DestDir']
            if rpc.editqueue('HistoryDelete', 0, "", [tryInt(nzb_id)]):
                shutil.rmtree(path, True)
        except:
            log.error('Failed deleting: %s', traceback.format_exc(0))
            return False

        return True
