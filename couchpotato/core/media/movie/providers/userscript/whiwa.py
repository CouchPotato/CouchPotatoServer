from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'WHiWA'


class WHiWA(UserscriptBase):

    includes = ['http://whiwa.net/stats/movie/*']
