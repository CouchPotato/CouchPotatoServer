from couchpotato.core.providers.userscript.base import UserscriptBase


class MovieMeter(UserscriptBase):

    includes = ['http://*.moviemeter.nl/film/*', 'http://moviemeter.nl/film/*']
