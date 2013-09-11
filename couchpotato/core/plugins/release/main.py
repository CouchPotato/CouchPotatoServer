from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.scanner.main import Scanner
from couchpotato.core.settings.model import File, Release as Relea, Media
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import and_, or_
import os
import traceback

log = CPLog(__name__)


class Release(Plugin):

    def __init__(self):
        addEvent('release.add', self.add)

        addApiView('release.download', self.download, docs = {
            'desc': 'Send a release manually to the downloaders',
            'params': {
                'id': {'type': 'id', 'desc': 'ID of the release object in release-table'}
            }
        })
        addApiView('release.delete', self.deleteView, docs = {
            'desc': 'Delete releases',
            'params': {
                'id': {'type': 'id', 'desc': 'ID of the release object in release-table'}
            }
        })
        addApiView('release.ignore', self.ignore, docs = {
            'desc': 'Toggle ignore, for bad or wrong releases',
            'params': {
                'id': {'type': 'id', 'desc': 'ID of the release object in release-table'}
            }
        })
        addApiView('release.for_movie', self.forMovieView, docs = {
            'desc': 'Returns all releases for a movie. Ordered by score(desc)',
            'params': {
                'id': {'type': 'id', 'desc': 'ID of the movie'}
            }
        })

        addEvent('release.for_movie', self.forMovie)
        addEvent('release.delete', self.delete)
        addEvent('release.clean', self.clean)

    def add(self, group):

        db = get_session()

        identifier = '%s.%s.%s' % (group['library']['identifier'], group['meta_data'].get('audio', 'unknown'), group['meta_data']['quality']['identifier'])


        done_status, snatched_status = fireEvent('status.get', ['done', 'snatched'], single = True)

        # Add movie
        movie = db.query(Media).filter_by(library_id = group['library'].get('id')).first()
        if not movie:
            movie = Media(
                library_id = group['library'].get('id'),
                profile_id = 0,
                status_id = done_status.get('id')
            )
            db.add(movie)
            db.commit()

        # Add Release
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
        added_files = []
        for type in group['files']:
            for cur_file in group['files'][type]:
                added_file = self.saveFile(cur_file, type = type, include_media_info = type is 'movie')
                added_files.append(added_file.get('id'))

        # Add the release files in batch
        try:
            added_files = db.query(File).filter(or_(*[File.id == x for x in added_files])).all()
            rel.files.extend(added_files)
            db.commit()
        except:
            log.debug('Failed to attach "%s" to release: %s', (added_files, traceback.format_exc()))

        fireEvent('movie.restatus', movie.id)

        return True


    def saveFile(self, filepath, type = 'unknown', include_media_info = False):

        properties = {}

        # Get media info for files
        if include_media_info:
            properties = {}

        # Check database and update/insert if necessary
        return fireEvent('file.add', path = filepath, part = fireEvent('scanner.partnumber', file, single = True), type_tuple = Scanner.file_types.get(type), properties = properties, single = True)

    def deleteView(self, id = None, **kwargs):

        return {
            'success': self.delete(id)
        }

    def delete(self, id):

        db = get_session()

        rel = db.query(Relea).filter_by(id = id).first()
        if rel:
            rel.delete()
            db.commit()
            return True

        return False

    def clean(self, id):

        db = get_session()

        rel = db.query(Relea).filter_by(id = id).first()
        if rel:
            for release_file in rel.files:
                if not os.path.isfile(ss(release_file.path)):
                    db.delete(release_file)
            db.commit()

            if len(rel.files) == 0:
                self.delete(id)

            return True

        return False

    def ignore(self, id = None, **kwargs):

        db = get_session()

        rel = db.query(Relea).filter_by(id = id).first()
        if rel:
            ignored_status, failed_status, available_status = fireEvent('status.get', ['ignored', 'failed', 'available'], single = True)
            rel.status_id = available_status.get('id') if rel.status_id in [ignored_status.get('id'), failed_status.get('id')] else ignored_status.get('id')
            db.commit()

        return {
            'success': True
        }

    def download(self, id = None, **kwargs):

        db = get_session()

        snatched_status, done_status = fireEvent('status.get', ['snatched', 'done'], single = True)

        rel = db.query(Relea).filter_by(id = id).first()
        if rel:
            item = {}
            for info in rel.info:
                item[info.identifier] = info.value

            fireEvent('notify.frontend', type = 'release.download', data = True, message = 'Snatching "%s"' % item['name'])

            # Get matching provider
            provider = fireEvent('provider.belongs_to', item['url'], provider = item.get('provider'), single = True)

            if not item.get('protocol'):
                item['protocol'] = item['type']
                item['type'] = 'movie'

            if item.get('protocol') != 'torrent_magnet':
                item['download'] = provider.loginDownload if provider.urls.get('login') else provider.download

            success = fireEvent('searcher.download', data = item, movie = rel.movie.to_dict({
                'profile': {'types': {'quality': {}}},
                'releases': {'status': {}, 'quality': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {}
            }), manual = True, single = True)

            if success:
                db.expunge_all()
                rel = db.query(Relea).filter_by(id = id).first() # Get release again

                if rel.status_id != done_status.get('id'):
                    rel.status_id = snatched_status.get('id')
                    db.commit()

                fireEvent('notify.frontend', type = 'release.download', data = True, message = 'Successfully snatched "%s"' % item['name'])

            return {
                'success': success
            }
        else:
            log.error('Couldn\'t find release with id: %s', id)

        return {
            'success': False
        }

    def forMovie(self, id = None):

        db = get_session()

        releases_raw = db.query(Relea) \
            .options(joinedload_all('info')) \
            .options(joinedload_all('files')) \
            .filter(Relea.movie_id == id) \
            .all()

        releases = [r.to_dict({'info':{}, 'files':{}}) for r in releases_raw]
        releases = sorted(releases, key = lambda k: k['info'].get('score', 0), reverse = True)

        return releases

    def forMovieView(self, id = None, **kwargs):

        releases = self.forMovie(id)

        return {
            'releases': releases,
            'success': True
        }

