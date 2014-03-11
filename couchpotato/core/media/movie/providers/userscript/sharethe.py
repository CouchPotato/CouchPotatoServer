from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'ShareThe'


class ShareThe(UserscriptBase):

    includes = ['http://*.sharethe.tv/movies/*', 'http://sharethe.tv/movies/*']
