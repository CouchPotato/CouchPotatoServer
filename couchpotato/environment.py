from couchpotato.core.loader import Loader
from couchpotato.core.settings import Settings
import flask

class Env:

    ''' Environment variables '''
    _debug = False
    _settings = Settings()
    _loader = Loader()
    _options = None
    _args = None
    _quiet = False
    _deamonize = False

    ''' Data paths and directories '''
    _app_dir = ""
    _data_dir = ""
    _cache_dir = ""
    _db_path = ""

    @staticmethod
    def doDebug():
        return Env._debug

    @staticmethod
    def get(attr):
        return getattr(Env, '_' + attr)

    @staticmethod
    def set(attr, value):
        return setattr(Env, '_' + attr, value)

    @staticmethod
    def setting(attr, section = 'global', value = None, default = ''):

        # Return setting
        if value == None:
            return Env.get('settings').get(attr, default = default, section = section)

        # Set setting
        s = Env.get('settings')
        s.set(section, attr, value)
        return s

    @staticmethod
    def getParams():
        return getattr(flask.request, 'args')

    @staticmethod
    def getParam(attr, default = None):
        return getattr(flask.request, 'args').get(attr, default)
