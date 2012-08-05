from couchpotato.core.providers.userscript.base import UserscriptBase


class MoviesIO(UserscriptBase):

    includes = ['*://movies.io/m/*']
