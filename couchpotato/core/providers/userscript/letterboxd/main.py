from couchpotato.core.providers.userscript.base import UserscriptBase


class Letterboxd(UserscriptBase):

    includes = ['*://letterboxd.com/film/*']
