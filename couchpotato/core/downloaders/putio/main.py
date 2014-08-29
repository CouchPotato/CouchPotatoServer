import shutil

from couchpotato.api import addApiView
from couchpotato.core._base.downloader.main import DownloaderBase
from couchpotato.core.logger import CPLog
import api as pio

log = CPLog(__name__)

autoload = 'Putiodownload'


class PutIO(DownloaderBase):
    protocol = ['torrent', 'torrent_magnet']
    status_support = False

    def __init__(self):
        addApiView('downloader.putio.getfrom', self.getFromPutio, docs = {
            'desc': 'Allows you to download file from prom Put.io',
        })

        addApiView('downloader.putio.auth_url', self.getAuthorizationUrl)

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
            callbackurl = 'http://' + self.conf('callback_host') + '/' + self.conf('url_base',
                                                                                   section = 'core') + '/api/' + self.conf(
                'api_key', section = 'core') + '/downloader.putiodownload.getfrom/'
        client.Transfer.add_url(url, callback_url = callbackurl)

        return True

    def test(self):
        try:
            client = pio.Client(self.conf('oauth_token'))
            if client.File.list():
                return True
        except:
            log.info('Failed to get file listing, check OAUTH_TOKEN')
            return False

    def getAuthorizationUrl(self):
        # See notification/twitter
        pass

    def getCredentials(self):
        # Save oauth_token here to settings
        pass

    def getAllDownloadStatus(self, ids):
        # See other downloaders for examples

        # Check putio for status

        # Check "getFromPutio" progress
        pass

    def getFromPutio(self, **kwargs):

        log.info('Put.io Download has been called')
        client = pio.Client(self.conf('oauth_token'))
        files = client.File.list()

        tempdownloaddir = self.conf('tempdownload_dir')
        downloaddir = self.conf('download_dir')

        for f in files:
            if str(f.id) == str(kwargs.get('file_id')):
                # Need to read this in from somewhere
                client.File.download(f, dest = tempdownloaddir, delete_after_download = self.conf('delete_file'))
                shutil.move(tempdownloaddir + "/" + str(f.name), downloaddir)

        # Mark status of file_id as "done" here for getAllDownloadStatus

        return True
