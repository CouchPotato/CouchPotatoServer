import shutil

from couchpotato.api import addApiView
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
        #I can't figure out how to pass this into getCredentials so I'm saving it here
        self.apicallhost = host;
        oauth = pio.AuthHelper(client_id=self.client_id,client_secret=self.client_secret,redirect_uri=callback_url)
        resp = oauth.authentication_url
        log.info ('reps is %s,', resp)
        return { 
            'success': True,
            'url': resp,
        }


    def getCredentials(self, **kwargs):
        code = kwargs.get('code')
        log.info('getCredentials Called with code: %s', code)
        callback_url = cleanHost(self.apicallhost)  + '%sdownloader.putio.credentials/' % (Env.get('api_base').lstrip('/'))
        log.info('callback is %s',callback_url)
        oauth = pio.AuthHelper(client_id=self.client_id,client_secret=self.client_secret,redirect_uri=callback_url)
        oauth_token = oauth.get_access_token(code)
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
