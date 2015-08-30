from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'Trakt'


class Trakt(UserscriptBase):

    version = 2

    includes = ['*://trakt.tv/movies/*', '*://*.trakt.tv/movies/*']
    excludes = ['*://trakt.tv/movies/*/*', '*://*.trakt.tv/movies/*/*']
