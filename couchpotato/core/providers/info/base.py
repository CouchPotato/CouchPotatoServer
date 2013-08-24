from couchpotato.core.providers.base import Provider


class MovieProvider(Provider):
    type = 'movie'


class ShowProvider(Provider):
    type = 'show'
