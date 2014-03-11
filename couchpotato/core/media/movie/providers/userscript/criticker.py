from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'Criticker'


class Criticker(UserscriptBase):

    includes = ['http://www.criticker.com/film/*']
