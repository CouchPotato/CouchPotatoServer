from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import md5, getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.scanner.main import Scanner
from couchpotato.core.settings.model import FileType, File
from couchpotato.environment import Env
from tornado.web import StaticFileHandler
import os.path
import time
import traceback

log = CPLog(__name__)


class FileManager(Plugin):

    def __init__(self):
        addEvent('file.add', self.add)
        addEvent('file.download', self.download)
        addEvent('file.types', self.getTypes)

        addApiView('file.cache/(.*)', self.showCacheFile, static = True, docs = {
            'desc': 'Return a file from the cp_data/cache directory',
            'params': {
                'filename': {'desc': 'path/filename of the wanted file'}
            },
            'return': {'type': 'file'}
        })

        addApiView('file.types', self.getTypesView, docs = {
            'desc': 'Return a list of all the file types and their ids.',
            'return': {'type': 'object', 'example': """{
    'types': [
        {
            "identifier": "poster_original",
            "type": "image",
            "id": 1,
            "name": "Poster_original"
        },
        {
            "identifier": "poster",
            "type": "image",
            "id": 2,
            "name": "Poster"
        },
        etc
    ]
}"""}
        })

        addEvent('app.load', self.cleanup)
        addEvent('app.load', self.init)

    def init(self):

        for type_tuple in Scanner.file_types.values():
            self.getType(type_tuple)

    def cleanup(self):

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
            db.rollback()
        finally:
            db.close()

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

    def add(self, path = '', part = 1, type_tuple = (), available = 1, properties = None):
        if not properties: properties = {}

        try:
            db = get_session()
            type_id = self.getType(type_tuple).get('id')

            f = db.query(File).filter(File.path == toUnicode(path)).first()
            if not f:
                f = File()
                db.add(f)

            f.path = toUnicode(path)
            f.part = part
            f.available = available
            f.type_id = type_id

            db.commit()

            file_dict = f.to_dict()

            return file_dict
        except:
            log.error('Failed adding file: %s, %s', (path, traceback.format_exc()))
            db.rollback()
        finally:
            db.close()

    def getType(self, type_tuple):

        try:
            db = get_session()
            type_type, type_identifier = type_tuple

            ft = db.query(FileType).filter_by(identifier = type_identifier).first()
            if not ft:
                ft = FileType(
                    type = toUnicode(type_type),
                    identifier = type_identifier,
                    name = toUnicode(type_identifier[0].capitalize() + type_identifier[1:])
                )
                db.add(ft)
                db.commit()

            type_dict = ft.to_dict()

            return type_dict
        except:
            log.error('Failed getting type: %s, %s', (type_tuple, traceback.format_exc()))
            db.rollback()
        finally:
            db.close()


    def getTypes(self):

        db = get_session()

        results = db.query(FileType).all()

        types = []
        for type_object in results:
            types.append(type_object.to_dict())

        return types

    def getTypesView(self, **kwargs):

        return {
            'types': self.getTypes()
        }
