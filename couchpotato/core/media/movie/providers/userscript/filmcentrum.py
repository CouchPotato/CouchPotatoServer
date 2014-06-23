from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'FilmCentrum'


class FilmCentrum(UserscriptBase):

    includes = ['*://filmcentrum.nl/films/*']
