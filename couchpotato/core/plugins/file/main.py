from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import md5, getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import File
from couchpotato.environment import Env
from tornado.web import StaticFileHandler
import os.path
import time
import traceback

log = CPLog(__name__)


class FileManager(Plugin):

    def __init__(self):
        addEvent('file.download', self.download)

        addApiView('file.cache/(.*)', self.showCacheFile, static = True, docs = {
            'desc': 'Return a file from the cp_data/cache directory',
            'params': {
                'filename': {'desc': 'path/filename of the wanted file'}
            },
            'return': {'type': 'file'}
        })

    def cleanup(self):
        # TODO: unused

        # Wait a bit after starting before cleanup
        time.sleep(3)
        log.debug('Cleaning up unused files')

        try:
            db = get_session()
            for root, dirs, walk_files in os.walk(Env.get('cache_dir')):
                for filename in walk_files:
                    if os.path.splitext(filename)[1] in ['.png', '.jpg', '.jpeg']:
                        file_path = os.path.join(root, filename)
                        f = db.query(File).filter(File.path == toUnicode(file_path)).first()
                        if not f:
                            os.remove(file_path)
        except:
            log.error('Failed removing unused file: %s', traceback.format_exc())

    def showCacheFile(self, route, **kwargs):
        Env.get('app').add_handlers(".*$", [('%s%s' % (Env.get('api_base'), route), StaticFileHandler, {'path': Env.get('cache_dir')})])

    def download(self, url = '', dest = None, overwrite = False, urlopen_kwargs = None):
        if not urlopen_kwargs: urlopen_kwargs = {}

        if not dest: # to Cache
            dest = os.path.join(Env.get('cache_dir'), '%s.%s' % (md5(url), getExt(url)))

        if not overwrite and os.path.isfile(dest):
            return dest

        try:
            filedata = self.urlopen(url, **urlopen_kwargs)
        except:
            log.error('Failed downloading file %s: %s', (url, traceback.format_exc()))
            return False

        self.createFile(dest, filedata, binary = True)
        return dest
