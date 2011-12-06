from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.request import getParam, jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.scanner.main import Scanner
from couchpotato.core.settings.model import File, Release as Relea, Movie
from sqlalchemy.sql.expression import and_, or_

log = CPLog(__name__)


class Release(Plugin):

    def __init__(self):
        addEvent('release.add', self.add)

        addApiView('release.download', self.download)
        addApiView('release.delete', self.delete)

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

        # Add Release
        snatched_status = fireEvent('status.get', 'snatched', single = True)
        rel = db.query(Relea).filter(
            or_(
                Relea.identifier == identifier,
                and_(Relea.identifier.startswith(group['library']['identifier']), Relea.status_id == snatched_status.get('id'))
            )
        ).first()
        if not rel:
            rel = Relea(
                identifier = identifier,
                movie = movie,
                quality_id = group['meta_data']['quality'].get('id'),
                status_id = done_status.get('id')
            )
            db.add(rel)
            db.commit()

        # Add each file type
        for type in group['files']:
            for cur_file in group['files'][type]:
                added_file = self.saveFile(cur_file, type = type, include_media_info = type is 'movie')
                try:
                    added_file = db.query(File).filter_by(id = added_file.get('id')).one()
                    rel.files.append(added_file)
                    db.commit()
                except Exception, e:
                    log.debug('Failed to attach "%s" to release: %s' % (cur_file, e))

        db.remove()


    def saveFile(self, filepath, type = 'unknown', include_media_info = False):

        properties = {}

        # Get media info for files
        if include_media_info:
            properties = {}

        # Check database and update/insert if necessary
        return fireEvent('file.add', path = filepath, part = fireEvent('scanner.partnumber', file, single = True), type = Scanner.file_types.get(type), properties = properties, single = True)

    def delete(self):

        db = get_session()
        id = getParam('id')

        rel = db.query(Relea).filter_by(id = id).first()
        if rel:
            rel.delete()
            db.commit()

        return jsonified({
            'success': True
        })

    def download(self):

        db = get_session()
        id = getParam('id')

        rel = db.query(Relea).filter_by(id = id).first()
        if rel:
            item = {}
            for info in rel.info:
                item[info.identifier] = info.value

            # Get matching provider
            provider = fireEvent('provider.belongs_to', item['url'], single = True)
            item['download'] = provider.download

            fireEvent('searcher.download', data = item, movie = rel.movie.to_dict({
                'profile': {'types': {'quality': {}}},
                'releases': {'status': {}, 'quality': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {}
            }))

            return jsonified({
                'success': True
            })
        else:
            log.error('Couldn\'t find release with id: %s' % id)

        return jsonified({
            'success': False
        })
