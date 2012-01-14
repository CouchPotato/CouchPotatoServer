from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import md5, getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import FileType, File
from couchpotato.environment import Env
from flask.helpers import send_from_directory
from sqlalchemy.sql.expression import or_
import os.path

log = CPLog(__name__)


class FileManager(Plugin):

    def __init__(self):
        addEvent('file.add', self.add)
        addEvent('file.download', self.download)
        addEvent('file.types', self.getTypes)

        addApiView('file.cache/<path:filename>', self.showImage)

    def showImage(self, filename = ''):

        cache_dir = Env.get('cache_dir')
        filename = os.path.basename(filename)

        return send_from_directory(cache_dir, filename)

    def download(self, url = '', dest = None, overwrite = False):

        try:
            filedata = self.urlopen(url)
        except:
            return False

        if not dest: # to Cache
            dest = os.path.join(Env.get('cache_dir'), '%s.%s' % (md5(url), getExt(url)))

        if overwrite or not os.path.isfile(dest):
            self.createFile(dest, filedata, binary = True)

        return dest

    def add(self, path = '', part = 1, type = (), available = 1, properties = {}):
        db = get_session()

        f = db.query(File).filter(or_(File.path == toUnicode(path), File.path == path)).first()
        if not f:
            f = File()
            db.add(f)

        f.path = path
        f.part = part
        f.available = available
        f.type_id = self.getType(type).id

        db.commit()

        file_dict = f.to_dict()

        return file_dict

    def getType(self, type):

        db = get_session()
        type, identifier = type

        ft = db.query(FileType).filter_by(identifier = identifier).first()
        if not ft:
            ft = FileType(
                type = type,
                identifier = identifier,
                name = identifier[0].capitalize() + identifier[1:]
            )

            db.add(ft)
            db.commit()

        return ft

    def getTypes(self):

        db = get_session()

        results = db.query(FileType).all()

        types = []
        for type in results:
            types.append(type.to_dict())

        return types
