import datetime

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
    downloadingList = []
    # This is the location on the Internet of the Oauth helper server
    oauthServerURL = "http://sabnzb.dumaresq.ca/index.cgi"


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
        # Note callback_host is NOT our address, it's the internet host that putio can call too
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
        target_url = oauthServerURL + "?target=" + callback_url
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
           if t.id in ids:
              log.debug('downloading list is %s', self.downloadingList)
              if t.status == "COMPLETED" and self.conf('download') == False :
                 status = 'completed'
              # So check if we are trying to download something
              elif t.status == "COMPLETED" and self.conf('download') == True:
                status = 'busy'
                # This is not ideal, right now if we are downloading anything we can't mark anything as completed
                # The name and ID don't match currently so I can't use those...
                if not self.downloadingList:
                  now = datetime.datetime.utcnow()
                  date_time = datetime.datetime.strptime(t.finished_at,"%Y-%m-%dT%H:%M:%S")
                  # We need to make sure a race condition didn't happen
                  if (now - date_time) > datetime.timedelta(minutes=5):
                    status = 'completed'
              else:
                 status = 'busy'
              release_downloads.append({
                    'id' : t.id,
                    'name': t.name,
                    'status': status,
                    'timeleft': t.estimated_time,
              })
            
              log.debug(release_downloads)
        return release_downloads


    def putioDownloader(self, fid):
        log.info('Put.io Real downloader called with file_id: %s',fid)
        client = pio.Client(self.conf('oauth_token'))
        log.debug('About to get file List')
        files = client.File.list()
        log.debug('File list is %s',files)
        downloaddir = self.conf('download_dir')
        for f in files:
            if str(f.id) == str(fid):
                client.File.download(f, dest = downloaddir, delete_after_download = self.conf('delete_file'))
                # Once the download is complete we need to remove it from the running list.
                self.downloadingList.remove(fid)

        return True


    def getFromPutio(self, **kwargs):
        file_id = str(kwargs.get('file_id'))
        log.info('Put.io Download has been called file_id is %s', file_id)
        if file_id not in self.downloadingList:
           self.downloadingList.append(file_id)
           fireEventAsync('putio.download',fid = file_id)
           return {
               'success': True,
           }
        return {
            'success': False,
        } 

