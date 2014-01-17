from couchpotato import get_session, md5
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import ss, toUnicode
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.scanner.main import Scanner
from couchpotato.core.settings.model import File, Release as Relea, Media, \
    ReleaseInfo
from couchpotato.environment import Env
from inspect import ismethod, isfunction
from sqlalchemy.exc import InterfaceError
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import and_, or_
import os
import time
import traceback

log = CPLog(__name__)


class Release(Plugin):

    def __init__(self):
        addEvent('release.add', self.add)

        addApiView('release.manual_download', self.manualDownload, docs = {
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

        addEvent('release.download', self.download)
        addEvent('release.try_download_result', self.tryDownloadResult)
        addEvent('release.create_from_search', self.createFromSearch)
        addEvent('release.for_movie', self.forMovie)
        addEvent('release.delete', self.delete)
        addEvent('release.clean', self.clean)
        addEvent('release.update_status', self.updateStatus)

        # Clean releases that didn't have activity in the last week
        addEvent('app.load', self.cleanDone)
        fireEvent('schedule.interval', 'movie.clean_releases', self.cleanDone, hours = 4)

    def cleanDone(self):

        log.debug('Removing releases from dashboard')

        now = time.time()
        week = 262080

        done_status, available_status, snatched_status, downloaded_status, ignored_status = \
            fireEvent('status.get', ['done', 'available', 'snatched', 'downloaded', 'ignored'], single = True)

        db = get_session()

        # get movies last_edit more than a week ago
        media = db.query(Media) \
            .filter(Media.status_id == done_status.get('id'), Media.last_edit < (now - week)) \
            .all()

        for item in media:
            for rel in item.releases:
                # Remove all available releases
                if rel.status_id in [available_status.get('id')]:
                    fireEvent('release.delete', id = rel.id, single = True)
                # Set all snatched and downloaded releases to ignored to make sure they are ignored when re-adding the move
                elif rel.status_id in [snatched_status.get('id'), downloaded_status.get('id')]:
                    self.updateStatus(id = rel.id, status = ignored_status)

        db.expire_all()

    def add(self, group):

        db = get_session()

        identifier = '%s.%s.%s' % (group['library']['identifier'], group['meta_data'].get('audio', 'unknown'), group['meta_data']['quality']['identifier'])


        done_status, snatched_status = fireEvent('status.get', ['done', 'snatched'], single = True)

        # Add movie
        media = db.query(Media).filter_by(library_id = group['library'].get('id')).first()
        if not media:
            media = Media(
                library_id = group['library'].get('id'),
                profile_id = 0,
                status_id = done_status.get('id')
            )
            db.add(media)
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
                movie = media,
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

        fireEvent('media.restatus', media.id)

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
            self.updateStatus(id, available_status if rel.status_id in [ignored_status.get('id'), failed_status.get('id')] else ignored_status)

        return {
            'success': True
        }

    def manualDownload(self, id = None, **kwargs):

        db = get_session()

        rel = db.query(Relea).filter_by(id = id).first()
        if not rel:
            log.error('Couldn\'t find release with id: %s', id)
            return {
                'success': False
            }

        item = {}
        for info in rel.info:
            item[info.identifier] = info.value

        fireEvent('notify.frontend', type = 'release.manual_download', data = True, message = 'Snatching "%s"' % item['name'])

        # Get matching provider
        provider = fireEvent('provider.belongs_to', item['url'], provider = item.get('provider'), single = True)

        # Backwards compatibility code
        if not item.get('protocol'):
            item['protocol'] = item['type']
            item['type'] = 'movie'

        if item.get('protocol') != 'torrent_magnet':
            item['download'] = provider.loginDownload if provider.urls.get('login') else provider.download

        success = self.download(data = item, media = rel.movie.to_dict({
            'profile': {'types': {'quality': {}}},
            'releases': {'status': {}, 'quality': {}},
            'library': {'titles': {}, 'files':{}},
            'files': {}
        }), manual = True)

        if success == True:
            db.expunge_all()
            rel = db.query(Relea).filter_by(id = id).first() # Get release again @RuudBurger why do we need to get it again??

            fireEvent('notify.frontend', type = 'release.manual_download', data = True, message = 'Successfully snatched "%s"' % item['name'])
        return {
            'success': success == True
        }

    def download(self, data, media, manual = False):

        # Backwards compatibility code
        if not data.get('protocol'):
            data['protocol'] = data['type']
            data['type'] = 'movie'

        # Test to see if any downloaders are enabled for this type
        downloader_enabled = fireEvent('download.enabled', manual, data, single = True)
        if not downloader_enabled:
            log.info('Tried to download, but none of the "%s" downloaders are enabled or gave an error', data.get('protocol'))
            return False

        # Download NZB or torrent file
        filedata = None
        if data.get('download') and (ismethod(data.get('download')) or isfunction(data.get('download'))):
            try:
                filedata = data.get('download')(url = data.get('url'), nzb_id = data.get('id'))
            except:
                log.error('Tried to download, but the "%s" provider gave an error: %s', (data.get('protocol'), traceback.format_exc()))
                return False

            if filedata == 'try_next':
                return filedata
            elif not filedata:
                return False

        # Send NZB or torrent file to downloader
        download_result = fireEvent('download', data = data, media = media, manual = manual, filedata = filedata, single = True)
        if not download_result:
            log.info('Tried to download, but the "%s" downloader gave an error', data.get('protocol'))
            return False
        log.debug('Downloader result: %s', download_result)

        snatched_status, done_status, downloaded_status, active_status = fireEvent('status.get', ['snatched', 'done', 'downloaded', 'active'], single = True)

        try:
            db = get_session()
            rls = db.query(Relea).filter_by(identifier = md5(data['url'])).first()
            if not rls:
                log.error('No release found to store download information in')
                return False

            renamer_enabled = Env.setting('enabled', 'renamer')

            # Save download-id info if returned
            if isinstance(download_result, dict):
                for key in download_result:
                    rls_info = ReleaseInfo(
                        identifier = 'download_%s' % key,
                        value = toUnicode(download_result.get(key))
                    )
                    rls.info.append(rls_info)
                db.commit()

            log_movie = '%s (%s) in %s' % (getTitle(media['library']), media['library']['year'], rls.quality.label)
            snatch_message = 'Snatched "%s": %s' % (data.get('name'), log_movie)
            log.info(snatch_message)
            fireEvent('%s.snatched' % data['type'], message = snatch_message, data = rls.to_dict())

            # Mark release as snatched
            if renamer_enabled:
                self.updateStatus(rls.id, status = snatched_status)

            # If renamer isn't used, mark media done if finished or release downloaded
            else:
                if media['status_id'] == active_status.get('id'):
                    finished = next((True for profile_type in media['profile']['types'] if \
                                     profile_type['quality_id'] == rls.quality.id and profile_type['finish']), False)
                    if finished:
                        log.info('Renamer disabled, marking media as finished: %s', log_movie)

                        # Mark release done
                        self.updateStatus(rls.id, status = done_status)

                        # Mark media done
                        mdia = db.query(Media).filter_by(id = media['id']).first()
                        mdia.status_id = done_status.get('id')
                        mdia.last_edit = int(time.time())
                        db.commit()

                        return True

                # Assume release downloaded
                self.updateStatus(rls.id, status = downloaded_status)

        except:
            log.error('Failed storing download status: %s', traceback.format_exc())
            return False

        return True

    def tryDownloadResult(self, results, media, quality_type, manual = False):
        ignored_status, failed_status = fireEvent('status.get', ['ignored', 'failed'], single = True)

        for rel in results:
            if not quality_type.get('finish', False) and quality_type.get('wait_for', 0) > 0 and rel.get('age') <= quality_type.get('wait_for', 0):
                log.info('Ignored, waiting %s days: %s', (quality_type.get('wait_for'), rel['name']))
                continue

            if rel['status_id'] in [ignored_status.get('id'), failed_status.get('id')]:
                log.info('Ignored: %s', rel['name'])
                continue

            if rel['score'] <= 0:
                log.info('Ignored, score to low: %s', rel['name'])
                continue

            downloaded = fireEvent('release.download', data = rel, media = media, manual = manual, single = True)
            if downloaded is True:
                return True
            elif downloaded != 'try_next':
                break

        return False

    def createFromSearch(self, search_results, media, quality_type):

        available_status = fireEvent('status.get', ['available'], single = True)
        db = get_session()

        found_releases = []

        for rel in search_results:

            rel_identifier = md5(rel['url'])
            found_releases.append(rel_identifier)

            rls = db.query(Relea).filter_by(identifier = rel_identifier).first()
            if not rls:
                rls = Relea(
                    identifier = rel_identifier,
                    movie_id = media.get('id'),
                    #media_id = media.get('id'),
                    quality_id = quality_type.get('quality_id'),
                    status_id = available_status.get('id')
                )
                db.add(rls)
            else:
                [db.delete(old_info) for old_info in rls.info]
                rls.last_edit = int(time.time())

            db.commit()

            for info in rel:
                try:
                    if not isinstance(rel[info], (str, unicode, int, long, float)):
                        continue

                    rls_info = ReleaseInfo(
                        identifier = info,
                        value = toUnicode(rel[info])
                    )
                    rls.info.append(rls_info)
                except InterfaceError:
                    log.debug('Couldn\'t add %s to ReleaseInfo: %s', (info, traceback.format_exc()))

            db.commit()

            rel['status_id'] = rls.status_id

        return found_releases

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

    def updateStatus(self, id, status = None):
        if not status: return False

        db = get_session()

        rel = db.query(Relea).filter_by(id = id).first()
        if rel and status and rel.status_id != status.get('id'):

            item = {}
            for info in rel.info:
                item[info.identifier] = info.value

            if rel.files:
                for file_item in rel.files:
                    if file_item.type.identifier == 'movie':
                        release_name = os.path.basename(file_item.path)
                        break
            else:
                release_name = item['name']
            #update status in Db
            log.debug('Marking release %s as %s', (release_name, status.get("label")))
            rel.status_id = status.get('id')
            rel.last_edit = int(time.time())
            db.commit()

            #Update all movie info as there is no release update function
            fireEvent('notify.frontend', type = 'release.update_status', data = rel.to_dict())

        return True
