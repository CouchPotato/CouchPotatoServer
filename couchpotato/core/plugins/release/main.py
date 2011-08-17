from couchpotato import get_session
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import File, Release, Movie
from sqlalchemy.sql.expression import and_, or_

log = CPLog(__name__)


class Release(Plugin):

    def __init__(self):
        addEvent('release.add', self.add)

    def add(self, group):
        db = get_session()

        identifier = '%s.%s.%s' % (group['library']['identifier'], group['meta_data'].get('audio', 'unknown'), group['meta_data']['quality']['identifier'])

        # Add movie
        done_status = fireEvent('status.get', 'done', single = True)
        movie = db.query(Movie).filter_by(library_id = group['library'].get('id')).first()
        if not movie:
            movie = Movie(
                library_id = group['library'].get('id'),
                profile_id = 0,
                status_id = done_status.get('id')
            )
            db.add(movie)
            db.commit()

        # Add release
        snatched_status = fireEvent('status.get', 'snatched', single = True)
        release = db.query(Release).filter(
            or_(
                Release.identifier == identifier,
                and_(Release.identifier.startswith(group['library']['identifier'], Release.status_id == snatched_status.get('id')))
            )
        ).first()
        if not release:
            release = Release(
                identifier = identifier,
                movie = movie,
                quality_id = group['meta_data']['quality'].get('id'),
                status_id = done_status.get('id')
            )
            db.add(release)
            db.commit()

        # Add each file type
        for type in group['files']:
            for file in group['files'][type]:
                added_file = self.saveFile(file, type = type, include_media_info = type is 'movie')
                try:
                    added_file = db.query(File).filter_by(id = added_file.get('id')).one()
                    release.files.append(added_file)
                    db.commit()
                except Exception, e:
                    log.debug('Failed to attach "%s" to release: %s' % (file, e))

        db.remove()


    def saveFile(self, file, type = 'unknown', include_media_info = False):

        properties = {}

        # Get media info for files
        if include_media_info:
            properties = {}

        # Check database and update/insert if necessary
        return fireEvent('file.add', path = file, part = self.getPartNumber(file), type = self.file_types[type], properties = properties, single = True)

