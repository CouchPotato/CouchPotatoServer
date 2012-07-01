from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.loader import Loader
from couchpotato.core.settings import Settings
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import sessionmaker
import os

class Env(object):

    _appname = 'CouchPotato'

    ''' Environment variables '''
    _encoding = 'UTF-8'
    _debug = False
    _dev = False
    _settings = Settings()
    _loader = Loader()
    _cache = None
    _options = None
    _args = None
    _quiet = False
    _deamonize = False
    _desktop = None
    _session = None

    ''' Data paths and directories '''
    _app_dir = ""
    _data_dir = ""
    _cache_dir = ""
    _db_path = ""
    _log_path = ""

    @staticmethod
    def doDebug():
        return Env._debug

    @staticmethod
    def get(attr):
        return getattr(Env, '_' + attr)

    @staticmethod
    def all():
        ret = ''
        for attr in ['encoding', 'debug', 'args', 'app_dir', 'data_dir', 'desktop', 'options']:
            ret += '%s=%s ' % (attr, Env.get(attr))

        return ret

    @staticmethod
    def set(attr, value):
        return setattr(Env, '_' + attr, value)

    @staticmethod
    def getSession(engine = None):
        existing_session = Env.get('session')
        if existing_session:
            return existing_session

        engine = Env.getEngine()
        session = scoped_session(sessionmaker(bind = engine))
        Env.set('session', session)

        return session

    @staticmethod
    def getEngine():
        return create_engine(Env.get('db_path'), echo = False, pool_recycle = 30)

    @staticmethod
    def setting(attr, section = 'core', value = None, default = '', type = None):

        s = Env.get('settings')

        # Return setting
        if value == None:
            return s.get(attr, default = default, section = section, type = type)

        # Set setting
        s.set(section, attr, value)
        s.save()

        return s

    @staticmethod
    def prop(identifier, value = None, default = None):
        s = Env.get('settings')
        if value == None:
            v = s.getProperty(identifier)
            return v if v else default

        s.setProperty(identifier, value)

    @staticmethod
    def getPermission(setting_type):
        perm = Env.get('settings').get('permission_%s' % setting_type, default = '0777')
        if perm[0] == '0':
            return int(perm, 8)
        else:
            return int(perm)

    @staticmethod
    def fireEvent(*args, **kwargs):
        return fireEvent(*args, **kwargs)

    @staticmethod
    def addEvent(*args, **kwargs):
        return addEvent(*args, **kwargs)

    @staticmethod
    def getPid():
        try:
            try:
                parent = os.getppid()
            except:
                parent = None
            return '%d %s' % (os.getpid(), '(%d)' % parent if parent and parent > 1 else '')
        except:
            return 0

    @staticmethod
    def getIdentifier():
        return '%s %s' % (Env.get('appname'), fireEvent('app.version', single = True))
