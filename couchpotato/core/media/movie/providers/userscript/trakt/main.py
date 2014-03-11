from couchpotato.core.media._base.providers.userscript.base import UserscriptBase


class Trakt(UserscriptBase):

    includes = ['http://trakt.tv/movie/*', 'http://*.trakt.tv/movie/*']
    excludes = ['http://trakt.tv/movie/*/*', 'http://*.trakt.tv/movie/*/*']
