from couchpotato.core.media._base.providers.userscript.base import UserscriptBase


class MoviesIO(UserscriptBase):

    includes = ['*://movies.io/m/*']
