from couchpotato.core.loader import Loader
from couchpotato.core.settings import Settings

class Env:

    ''' Environment variables '''
    _uses_git = False
    _debug = False
    _settings = Settings()
    _loader = Loader()
    _cache = None
    _options = None
    _args = None
    _quiet = False
    _deamonize = False
    _version = 0.5

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
    def set(attr, value):
        return setattr(Env, '_' + attr, value)

    @staticmethod
    def setting(attr, section = 'core', value = None, default = ''):

        s = Env.get('settings')

        # Return setting
        if value == None:
            return s.get(attr, default = default, section = section)

        # Set setting
        s.set(section, attr, value)
        s.save()

        return s

    @staticmethod
    def getPermission(type):
        return int(Env.get('settings').get('permission_%s' % type, default = 0777))
