from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'Letterboxd'


class Letterboxd(UserscriptBase):

    includes = ['*://letterboxd.com/film/*']
