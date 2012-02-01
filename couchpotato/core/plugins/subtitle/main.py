from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, FileType

log = CPLog(__name__)


class Subtitle(Plugin):

    def __init__(self):

        #addEvent('renamer.before', self.searchSingle)

    def searchLibrary(self):

        # Get all active and online movies
        db = get_session()

        library = db.query(Library).all()
        done_status = fireEvent('status.get', 'done', single = True)

        for movie in library.movies:

            for release in movie.releases:

                # get releases and their movie files
                if release.status_id is done_status.get('id'):

                    files = []
                    for file in release.files.filter(FileType.status.has(identifier = 'movie')).all():
                        files.append(file.path);

                    # get subtitles for those files
                    subtitles = fireEvent('subtitle.search', files = files, languages = self.getLanguages(), merge = True)

                    # do something with the returned subtitles
                    print subtitles


    def searchSingle(self, group):

        if self.isDisabled(): return

        subtitles = fireEvent('subtitle.search', files = group['files']['movie'], languages = self.getLanguages(), merge = True)

        # do something with the returned subtitles
        print subtitles

    def getLanguages(self):
        return self.conf('languages').split(',')
