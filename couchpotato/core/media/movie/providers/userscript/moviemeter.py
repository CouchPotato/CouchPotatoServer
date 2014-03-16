from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'MovieMeter'


class MovieMeter(UserscriptBase):

    includes = ['http://*.moviemeter.nl/film/*', 'http://moviemeter.nl/film/*']
