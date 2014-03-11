from couchpotato.core.media._base.providers.userscript.base import UserscriptBase


class Letterboxd(UserscriptBase):

    includes = ['*://letterboxd.com/film/*']
