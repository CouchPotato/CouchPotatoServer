from couchpotato.core.settings import Settings

class Env:
    _debug = False
    _settings = Settings()
    _options = None
    _args = None
    _quiet = False

    _app_dir = ""
    _data_dir = ""
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
