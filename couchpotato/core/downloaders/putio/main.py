import shutil

from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEventAsync
from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
import api as pio

log = CPLog(__name__)

autoload = 'Putiodownload'


class PutIO(DownloaderBase):
    protocol = ['torrent', 'torrent_magnet']
    status_support = True
    client_id = '1575'
    client_secret = '132qbpseq1ymwn83wus4'

    def __init__(self):
        addApiView('downloader.putio.getfrom', self.getFromPutio, docs = {
            'desc': 'Allows you to download file from prom Put.io',
        })

        addApiView('downloader.putio.auth_url', self.getAuthorizationUrl)
        addApiView('downloader.putio.credentials', self.getCredentials)
        addEvent('putio.download', self.putioDownloader)

        return super(PutIO, self).__init__()

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

        log.info('Sending "%s" to put.io', data.get('name'))
        url = data.get('url')

        client = pio.Client(self.conf('oauth_token'))

        # Need to constuct a the API url a better way.
        callbackurl = None
        if self.conf('download'):
            callbackurl = 'http://' + self.conf('callback_host') + '/' + '%sdownloader.putio.getfrom/' %Env.get('api_base'.strip('/')) 
        resp = client.Transfer.add_url(url, callback_url = callbackurl)
        log.debug('resp is %s', resp.id);
        return self.downloadReturnId(resp.id) 

    def test(self):
        try:
            client = pio.Client(self.conf('oauth_token'))
            if client.File.list():
                return True
        except:
            log.info('Failed to get file listing, check OAUTH_TOKEN')
            return False

    def getAuthorizationUrl(self, host = None, **kwargs):
        callback_url = cleanHost(host) + '%sdownloader.putio.credentials/' % (Env.get('api_base').lstrip('/'))
        log.info('callback_url is %s', callback_url)
        target_url = "http://sabnzbd.dumaresq.ca/index.cgi?target=" + callback_url
        log.info('target_url is %s', target_url)
        return { 
            'success': True,
            'url': target_url,
        }


    def getCredentials(self, **kwargs):
        oauth_token = kwargs.get('oauth')
        if not oauth_token:
          return 'redirect', Env.get('web_base') + 'settigs/downloaders/'
        log.info('oauth_token is: %s', oauth_token)
        self.conf('oauth_token', value = oauth_token);
        return 'redirect', Env.get('web_base') + 'settings/downloaders/'

    def getAllDownloadStatus(self, ids):
	log.debug('Checking putio download status.')
        client = pio.Client(self.conf('oauth_token'))
        transfers = client.Transfer.list()
        log.debug(transfers);
        release_downloads = ReleaseDownloadList(self)
        for t in transfers:
           if t.status == "COMPLETED" and self.conf('download') == False :
              status = 'completed'
           else:
              #status = t.status.lower()
              status = 'busy'
           release_downloads.append({
                 'id' : t.id,
                 'name': t.name,
                 'status': status,
                 'timeleft': t.estimated_time,
           })
            
        log.info(release_downloads)
        # Check "getFromPutio" progress
        return release_downloads

    def putioDownloader(self, fid):
        log.info('Put.io Real downloader called with file_id: %s',fid)
        client = pio.Client(self.conf('oauth_token'))
        log.debug('About to get file List')
        files = client.File.list()
        log.debug('File list is %s',files)
        tempdownloaddir = self.conf('tempdownload_dir')
        downloaddir = self.conf('download_dir')
        for f in files:
            if str(f.id) == str(fid):
                # Need to read this in from somewhere
                client.File.download(f, dest = tempdownloaddir, delete_after_download = self.conf('delete_file'))
                shutil.move(tempdownloaddir + "/" + str(f.name), downloaddir)

        # Mark status of file_id as "done" here for getAllDownloadStatus

        return True

    def getFromPutio(self, **kwargs):
        # This needs some checking so that we don't download the same file multiple times.
        # This needs to have a way to query if the download is still going
        # would be nice to be albe to check how much is downloaded and report that.
        file_id = str(kwargs.get('file_id'))
        log.info('Put.io Download has been called file_id is %s', file_id)
        fireEventAsync('putio.download',fid = file_id)
        # Mark status of file_id as "done" here for getAllDownloadStatus

        return {
            'success': True,
        }

