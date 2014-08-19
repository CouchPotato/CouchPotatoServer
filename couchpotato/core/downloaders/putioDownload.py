from __future__ import with_statement
import os
import traceback
import putio

from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core._base.downloader.main import DownloaderBase
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import getDownloadDir
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env

log = CPLog(__name__)

autoload = 'Putiodownload'


class Putiodownload(DownloaderBase):

    protocol = ['torrent', 'torrent_magnet']
    status_support = False 

    def __init__(self):
        addApiView('putiodownload.getfrom', self.getFromPutio, docs = {
            'desc': 'Allows you to download file from prom Put.io',
        })
        return super(Putiodownload,self).__init__()


    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}
	log.info ('Sending "%s" to put.io', data.get('name'))
	url = data.get('url')
        OAUTH_TOKEN = self.conf('oauth_token')
        client = putio.Client(OAUTH_TOKEN)
        # Need to constuct a the API url a better way.
        callbackurl = None 
        if self.conf('download'):
            callbackurl = 'http://'+self.conf('callback_host')+'/'+self.conf('url_base', section='core')+'/api/'+self.conf('api_key', section='core')+'/putiodownload.getfrom/'
        client.Transfer.add_url(url,callback_url=callbackurl)
        return True
    
    def test(self):
        OAUTH_TOKEN = self.conf('oauth_token')
        try: 
            client = putio.Client(OAUTH_TOKEN)
            if client.File.list():
                return True
        except:
            log.info('Failed to get file listing, check OAUTH_TOKEN')
            return False

    def getFromPutio(self, **kwargs):
       log.info('Put.io Download has been called')
       OAUTH_TOKEN = self.conf('oauth_token')
       client = putio.Client(OAUTH_TOKEN)
       files = client.File.list()
       delete = self.conf('detele_file')
       downloaddir = self.conf('download_dir')
       tempdownloaddir = self.conf('tempdownload_dir') 
       for f in files:
           if str(f.id) == str(kwargs.get('file_id')):
               # Need to read this in from somewhere
               client.File.download(f, dest=tempdownloaddir, delete_after_download=delete)
               shutil.move(tempdownloaddir+"/"+str(f.name),downloaddir)
       return True 
 
config = [{
    'name': 'putiodownload',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'putiodownload',
            'label': 'put.io Download',
            'description': 'This will start a torrent download on Put.io.  <BR>Note:  you must have a putio account and API',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
                {
                    'name': 'oauth_token',
                    'label': 'oauth_token',
                    'description': 'This is the OAUTH_TOKEN from your putio API',
                },
                {
                    'name': 'callback_host',
                    'description': 'This is used to generate the callback url',
                },
                {
                    'name': 'download',
                    'description': 'Set this to have CouchPotato download the file from Put.io',
                    'type': 'bool',
                    'default': 0,
                },
                {
                    'name': 'detele_file',
                    'description': 'Set this to remove the file from putio after sucessful download  Note: does nothing if you don\'t select download',
                    'type': 'bool',
                    'default': 0,
                },
		{
                    'name': 'download_dir',
                    'label': 'Download Directory',
                    'description': 'The Directory to download files to, does nothing if you don\'t select download',
		    'default': '/',
                },
		{
                    'name': 'tempdownload_dir',
                    'label': 'Temporary Download Directory',
                    'description': 'The Temporary Directory to download files to, does nothing if you don\'t select download',
		    'default': '/',
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
            ],
        }
    ],
}]
