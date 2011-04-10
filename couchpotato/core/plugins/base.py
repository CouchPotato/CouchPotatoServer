from couchpotato.environment import Env


class Plugin():

    def conf(self, attr):
        return Env.setting(attr, self.__class__.__name__.lower())
