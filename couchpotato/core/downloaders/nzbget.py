from base64 import standard_b64encode
from datetime import timedelta
import re
import shutil
import socket
import traceback
import xmlrpclib

from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import ss, sp
from couchpotato.core.helpers.variable import tryInt, md5, cleanHost
from couchpotato.core.logger import CPLog


log = CPLog(__name__)

autoload = 'NZBGet'


class NZBGet(DownloaderBase):

    protocol = ['nzb']
    rpc = 'xmlrpc'

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

        if not filedata:
            log.error('Unable to get NZB file: %s', traceback.format_exc())
            return False

        log.info('Sending "%s" to NZBGet.', data.get('name'))

        nzb_name = ss('%s.nzb' % self.createNzbName(data, media))

        rpc = self.getRPC()

        try:
            if rpc.writelog('INFO', 'CouchPotato connected to drop off %s.' % nzb_name):
                log.debug('Successfully connected to NZBGet')
            else:
                log.info('Successfully connected to NZBGet, but unable to send a message')
        except socket.error:
            log.error('NZBGet is not responding. Please ensure that NZBGet is running and host setting is correct.')
            return False
        except xmlrpclib.ProtocolError as e:
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
            nzb_id = md5(data['url'])  # about as unique as they come ;)
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

    def test(self):
        rpc = self.getRPC()

        try:
            if rpc.writelog('INFO', 'CouchPotato connected to test connection'):
                log.debug('Successfully connected to NZBGet')
            else:
                log.info('Successfully connected to NZBGet, but unable to send a message')
        except socket.error:
            log.error('NZBGet is not responding. Please ensure that NZBGet is running and host setting is correct.')
            return False
        except xmlrpclib.ProtocolError as e:
            if e.errcode == 401:
                log.error('Password is incorrect.')
            else:
                log.error('Protocol Error: %s', e)
            return False

        return True

    def getAllDownloadStatus(self, ids):

        log.debug('Checking NZBGet download status.')

        rpc = self.getRPC()

        try:
            if rpc.writelog('INFO', 'CouchPotato connected to check status'):
                log.debug('Successfully connected to NZBGet')
            else:
                log.info('Successfully connected to NZBGet, but unable to send a message')
        except socket.error:
            log.error('NZBGet is not responding. Please ensure that NZBGet is running and host setting is correct.')
            return []
        except xmlrpclib.ProtocolError as e:
            if e.errcode == 401:
                log.error('Password is incorrect.')
            else:
                log.error('Protocol Error: %s', e)
            return []

        # Get NZBGet data
        try:
            status = rpc.status()
            groups = rpc.listgroups()
            queue = rpc.postqueue(0)
            history = rpc.history()
        except:
            log.error('Failed getting data: %s', traceback.format_exc(1))
            return []

        release_downloads = ReleaseDownloadList(self)

        for nzb in groups:
            try:
                nzb_id = [param['Value'] for param in nzb['Parameters'] if param['Name'] == 'couchpotato'][0]
            except:
                nzb_id = nzb['NZBID']

            if nzb_id in ids:
                log.debug('Found %s in NZBGet download queue', nzb['NZBFilename'])
                timeleft = -1
                try:
                    if nzb['ActiveDownloads'] > 0 and nzb['DownloadRate'] > 0 and not (status['DownloadPaused'] or status['Download2Paused']):
                        timeleft = str(timedelta(seconds = nzb['RemainingSizeMB'] / status['DownloadRate'] * 2 ^ 20))
                except:
                    pass

                release_downloads.append({
                    'id': nzb_id,
                    'name': nzb['NZBFilename'],
                    'original_status': 'DOWNLOADING' if nzb['ActiveDownloads'] > 0 else 'QUEUED',
                    # Seems to have no native API function for time left. This will return the time left after NZBGet started downloading this item
                    'timeleft': timeleft,
                })

        for nzb in queue:  # 'Parameters' is not passed in rpc.postqueue
            if nzb['NZBID'] in ids:
                log.debug('Found %s in NZBGet postprocessing queue', nzb['NZBFilename'])
                release_downloads.append({
                    'id': nzb['NZBID'],
                    'name': nzb['NZBFilename'],
                    'original_status': nzb['Stage'],
                    'timeleft': str(timedelta(seconds = 0)) if not status['PostPaused'] else -1,
                })

        for nzb in history:
            try:
                nzb_id = [param['Value'] for param in nzb['Parameters'] if param['Name'] == 'couchpotato'][0]
            except:
                nzb_id = nzb['NZBID']

            if nzb_id in ids:
                log.debug('Found %s in NZBGet history. ParStatus: %s, ScriptStatus: %s, Log: %s', (nzb['NZBFilename'] , nzb['ParStatus'], nzb['ScriptStatus'] , nzb['Log']))
                release_downloads.append({
                    'id': nzb_id,
                    'name': nzb['NZBFilename'],
                    'status': 'completed' if nzb['ParStatus'] in ['SUCCESS', 'NONE'] and nzb['ScriptStatus'] in ['SUCCESS', 'NONE'] else 'failed',
                    'original_status': nzb['ParStatus'] + ', ' + nzb['ScriptStatus'],
                    'timeleft': str(timedelta(seconds = 0)),
                    'folder': sp(nzb['DestDir'])
                })

        return release_downloads

    def removeFailed(self, release_download):

        log.info('%s failed downloading, deleting...', release_download['name'])

        rpc = self.getRPC()

        try:
            if rpc.writelog('INFO', 'CouchPotato connected to delete some history'):
                log.debug('Successfully connected to NZBGet')
            else:
                log.info('Successfully connected to NZBGet, but unable to send a message')
        except socket.error:
            log.error('NZBGet is not responding. Please ensure that NZBGet is running and host setting is correct.')
            return False
        except xmlrpclib.ProtocolError as e:
            if e.errcode == 401:
                log.error('Password is incorrect.')
            else:
                log.error('Protocol Error: %s', e)
            return False

        try:
            history = rpc.history()
            nzb_id = None
            path = None

            for hist in history:
                for param in hist['Parameters']:
                    if param['Name'] == 'couchpotato' and param['Value'] == release_download['id']:
                        nzb_id = hist['ID']
                        path = hist['DestDir']

            if nzb_id and path and rpc.editqueue('HistoryDelete', 0, "", [tryInt(nzb_id)]):
                shutil.rmtree(path, True)
        except:
            log.error('Failed deleting: %s', traceback.format_exc(0))
            return False

        return True

    def getRPC(self):
        url = cleanHost(host = self.conf('host'), ssl = self.conf('ssl'), username = self.conf('username'), password = self.conf('password')) + self.rpc
        return xmlrpclib.ServerProxy(url)


config = [{
    'name': 'nzbget',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'nzbget',
            'label': 'NZBGet',
            'description': 'Use <a href="http://nzbget.sourceforge.net/Main_Page" target="_blank">NZBGet</a> to download NZBs.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'nzb',
                },
                {
                    'name': 'host',
                    'default': 'localhost:6789',
                    'description': 'Hostname with port. Usually <strong>localhost:6789</strong>',
                },
                {
                    'name': 'ssl',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Use HyperText Transfer Protocol Secure, or <strong>https</strong>',
                },
                {
                    'name': 'username',
                    'default': 'nzbget',
                    'advanced': True,
                    'description': 'Set a different username to connect. Default: nzbget',
                },
                {
                    'name': 'password',
                    'type': 'password',
                    'description': 'Default NZBGet password is <i>tegbzn6789</i>',
                },
                {
                    'name': 'category',
                    'default': 'Movies',
                    'description': 'The category CP places the nzb in. Like <strong>movies</strong> or <strong>couchpotato</strong>',
                },
                {
                    'name': 'priority',
                    'advanced': True,
                    'default': '0',
                    'type': 'dropdown',
                    'values': [('Very Low', -100), ('Low', -50), ('Normal', 0), ('High', 50), ('Very High', 100)],
                    'description': 'Only change this if you are using NZBget 9.0 or higher',
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
                {
                    'name': 'delete_failed',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Delete a release after the download has failed.',
                },
            ],
        }
    ],
}]
