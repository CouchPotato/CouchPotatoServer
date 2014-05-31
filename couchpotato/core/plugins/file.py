import os.path
import traceback

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import md5, getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from tornado.web import StaticFileHandler


log = CPLog(__name__)

autoload = 'FileManager'


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

        fireEvent('schedule.interval', 'file.cleanup', self.cleanup, hours = 24)

    def cleanup(self):

        # Wait a bit after starting before cleanup
        log.debug('Cleaning up unused files')

        try:
            db = get_db()
            cache_dir = Env.get('cache_dir')
            medias = db.all('media', with_doc = True)

            files = []
            for media in medias:
                file_dict = media['doc'].get('files', {})
                for x in file_dict.keys():
                    files.extend(file_dict[x])

            for f in os.listdir(cache_dir):
                if os.path.splitext(f.name)[1] in ['.png', '.jpg', '.jpeg']:
                    file_path = os.path.join(cache_dir, f.name)
                    if toUnicode(file_path) not in files:
                        os.remove(file_path)
        except:
            log.error('Failed removing unused file: %s', traceback.format_exc())

    def showCacheFile(self, route, **kwargs):
        Env.get('app').add_handlers(".*$", [('%s%s' % (Env.get('api_base'), route), StaticFileHandler, {'path': Env.get('cache_dir')})])

    def download(self, url = '', dest = None, overwrite = False, urlopen_kwargs = None):
        if not urlopen_kwargs: urlopen_kwargs = {}

        if not dest:  # to Cache
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
