from couchpotato.core.providers.userscript.base import UserscriptBase


class ShareThe(UserscriptBase):

    includes = ['http://*.sharethe.tv/movies/*', 'http://sharethe.tv/movies/*']
