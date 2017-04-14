import xmlrpclib
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.logger import CPLog

log = CPLog(__name__)


def true_false(val):
    lookup = {
        True: 'true',
        False: 'false',
    }
    return lookup.get(val, 'false')


class Aria2(Downloader):

    type = ['http']

    def download(self, data={}, movie={}, manual=False, filedata=None):
        log.info('Sending "%s" to aria2', data.get('name'))

        s = xmlrpclib.ServerProxy('http://%s/rpc' % self.conf('host'))
        return s.aria2.addUri([data['url']], {'pause': true_false(self.conf('pause'))})

    def getAllDownloadStatus(self):
        """
        status = {'id': '', 'name': '', 'status': '', 'original_status': '', 'timeleft': ''}
        """
        log.debug('Checking aria2 download status...')

        statuses = []

        return statuses

    def removeFailed(self, item):
        if not self.conf('delete_failed', default=True):
            return False

        log.info('%s failed downloading, deleting...', item['name'])

        return True
