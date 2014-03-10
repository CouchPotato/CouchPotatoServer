from couchpotato.core.providers.userscript.base import UserscriptBase


class Trakt(UserscriptBase):

    includes = ['http://trakt.tv/movie/*', 'http://*.trakt.tv/movie/*']
    excludes = ['http://trakt.tv/movie/*/*', 'http://*.trakt.tv/movie/*/*']
