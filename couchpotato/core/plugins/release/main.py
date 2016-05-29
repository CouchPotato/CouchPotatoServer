from inspect import ismethod, isfunction
import os
import time
import traceback

from CodernityDB.database import RecordDeleted, RecordNotFound
from couchpotato import md5, get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import toUnicode, sp
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from .index import ReleaseIndex, ReleaseStatusIndex, ReleaseIDIndex, ReleaseDownloadIndex
from couchpotato.environment import Env


log = CPLog(__name__)


class Release(Plugin):

    _database = {
        'release': ReleaseIndex,
        'release_status': ReleaseStatusIndex,
        'release_identifier': ReleaseIDIndex,
        'release_download': ReleaseDownloadIndex
    }

    def __init__(self):
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

        addEvent('release.add', self.add)
        addEvent('release.download', self.download)
        addEvent('release.try_download_result', self.tryDownloadResult)
        addEvent('release.create_from_search', self.createFromSearch)
        addEvent('release.delete', self.delete)
        addEvent('release.clean', self.clean)
        addEvent('release.update_status', self.updateStatus)
        addEvent('release.with_status', self.withStatus)
        addEvent('release.for_media', self.forMedia)

        # Clean releases that didn't have activity in the last week
        addEvent('app.load', self.cleanDone, priority = 1000)
        fireEvent('schedule.interval', 'movie.clean_releases', self.cleanDone, hours = 12)

    def cleanDone(self):
        log.debug('Removing releases from dashboard')

        now = time.time()
        week = 604800

        db = get_db()

        # Get (and remove) parentless releases
        releases = db.all('release', with_doc = False)
        media_exist = []
        reindex = 0
        for release in releases:
            if release.get('key') in media_exist:
                continue

            try:

                try:
                    doc = db.get('id', release.get('_id'))
                except RecordDeleted:
                    reindex += 1
                    continue

                db.get('id', release.get('key'))
                media_exist.append(release.get('key'))

                try:
                    if doc.get('status') == 'ignore':
                        doc['status'] = 'ignored'
                        db.update(doc)
                except:
                    log.error('Failed fixing mis-status tag: %s', traceback.format_exc())
            except ValueError:
                fireEvent('database.delete_corrupted', release.get('key'), traceback_error = traceback.format_exc(0))
                reindex += 1
            except RecordDeleted:
                db.delete(doc)
                log.debug('Deleted orphaned release: %s', doc)
                reindex += 1
            except:
                log.debug('Failed cleaning up orphaned releases: %s', traceback.format_exc())

        if reindex > 0:
            db.reindex()

        del media_exist

        # get movies last_edit more than a week ago
        medias = fireEvent('media.with_status', ['done', 'active'], single = True)

        for media in medias:
            if media.get('last_edit', 0) > (now - week):
                continue

            for rel in self.forMedia(media['_id']):

                # Remove all available releases
                if rel['status'] in ['available']:
                    self.delete(rel['_id'])

                # Set all snatched and downloaded releases to ignored to make sure they are ignored when re-adding the media
                elif rel['status'] in ['snatched', 'downloaded']:
                    self.updateStatus(rel['_id'], status = 'ignored')

            if 'recent' in media.get('tags', []):
                fireEvent('media.untag', media.get('_id'), 'recent', single = True)

    def add(self, group, update_info = True, update_id = None):

        try:
            db = get_db()

            release_identifier = '%s.%s.%s' % (group['identifier'], group['meta_data'].get('audio', 'unknown'), group['meta_data']['quality']['identifier'])

            # Add movie if it doesn't exist
            try:
                media = db.get('media', 'imdb-%s' % group['identifier'], with_doc = True)['doc']
            except:
                media = fireEvent('movie.add', params = {
                    'identifier': group['identifier'],
                    'profile_id': None,
                }, search_after = False, update_after = update_info, notify_after = False, status = 'done', single = True)

            release = None
            if update_id:
                try:
                    release = db.get('id', update_id)
                    release.update({
                        'identifier': release_identifier,
                        'last_edit': int(time.time()),
                        'status': 'done',
                    })
                except:
                    log.error('Failed updating existing release: %s', traceback.format_exc())
            else:

                # Add Release
                if not release:
                    release = {
                        '_t': 'release',
                        'media_id': media['_id'],
                        'identifier': release_identifier,
                        'quality': group['meta_data']['quality'].get('identifier'),
                        'is_3d': group['meta_data']['quality'].get('is_3d', 0),
                        'last_edit': int(time.time()),
                        'status': 'done'
                    }

                try:
                    r = db.get('release_identifier', release_identifier, with_doc = True)['doc']
                    r['media_id'] = media['_id']
                except:
                    log.debug('Failed updating release by identifier "%s". Inserting new.', release_identifier)
                    r = db.insert(release)

                # Update with ref and _id
                release.update({
                    '_id': r['_id'],
                    '_rev': r['_rev'],
                })

            # Empty out empty file groups
            release['files'] = dict((k, [toUnicode(x) for x in v]) for k, v in group['files'].items() if v)
            db.update(release)

            fireEvent('media.restatus', media['_id'], allowed_restatus = ['done'], single = True)

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False

    def deleteView(self, id = None, **kwargs):

        return {
            'success': self.delete(id)
        }

    def delete(self, release_id):

        try:
            db = get_db()
            rel = db.get('id', release_id)
            db.delete(rel)
            return True
        except RecordDeleted:
            log.debug('Already deleted: %s', release_id)
            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False

    def clean(self, release_id):

        try:
            db = get_db()
            rel = db.get('id', release_id)
            raw_files = rel.get('files')

            if len(raw_files) == 0:
                self.delete(rel['_id'])
            else:

                files = {}
                for file_type in raw_files:

                    for release_file in raw_files.get(file_type, []):
                        if os.path.isfile(sp(release_file)):
                            if file_type not in files:
                                files[file_type] = []
                            files[file_type].append(release_file)

                rel['files'] = files
                db.update(rel)

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False

    def ignore(self, id = None, **kwargs):

        db = get_db()

        try:
            if id:
                rel = db.get('id', id, with_doc = True)
                self.updateStatus(id, 'available' if rel['status'] in ['ignored', 'failed'] else 'ignored')

            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }

    def manualDownload(self, id = None, **kwargs):

        db = get_db()

        try:
            release = db.get('id', id)
            item = release['info']
            movie = db.get('id', release['media_id'])

            fireEvent('notify.frontend', type = 'release.manual_download', data = True, message = 'Snatching "%s"' % item['name'])

            # Get matching provider
            provider = fireEvent('provider.belongs_to', item['url'], provider = item.get('provider'), single = True)

            if item.get('protocol') != 'torrent_magnet':
                item['download'] = provider.loginDownload if provider.urls.get('login') else provider.download

            success = self.download(data = item, media = movie, manual = True)

            if success:
                fireEvent('notify.frontend', type = 'release.manual_download', data = True, message = 'Successfully snatched "%s"' % item['name'])

            return {
                'success': success == True
            }

        except:
            log.error('Couldn\'t find release with id: %s: %s', (id, traceback.format_exc()))
            return {
                'success': False
            }

    def download(self, data, media, manual = False):

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

        try:
            db = get_db()

            try:
                rls = db.get('release_identifier', md5(data['url']), with_doc = True)['doc']
            except:
                log.error('No release found to store download information in')
                return False

            renamer_enabled = Env.setting('enabled', 'renamer')

            # Save download-id info if returned
            if isinstance(download_result, dict):
                rls['download_info'] = download_result
                db.update(rls)

            log_movie = '%s (%s) in %s' % (getTitle(media), media['info'].get('year'), rls['quality'])
            snatch_message = 'Snatched "%s": %s from %s' % (data.get('name'), log_movie, (data.get('provider', '') + data.get('provider_extra', '')))
            log.info(snatch_message)
            fireEvent('%s.snatched' % data['type'], message = snatch_message, data = media)

            # Mark release as snatched
            if renamer_enabled:
                self.updateStatus(rls['_id'], status = 'snatched')

            # If renamer isn't used, mark media done if finished or release downloaded
            else:

                if media['status'] == 'active':
                    profile = db.get('id', media['profile_id'])
                    if fireEvent('quality.isfinish', {'identifier': rls['quality'], 'is_3d': rls.get('is_3d', False)}, profile, single = True):
                        log.info('Renamer disabled, marking media as finished: %s', log_movie)

                        # Mark release done
                        self.updateStatus(rls['_id'], status = 'done')

                        # Mark media done
                        fireEvent('media.restatus', media['_id'], single = True)

                        return True

                # Assume release downloaded
                self.updateStatus(rls['_id'], status = 'downloaded')

        except:
            log.error('Failed storing download status: %s', traceback.format_exc())
            return False

        return True

    def tryDownloadResult(self, results, media, quality_custom):

        wait_for = False
        let_through = False
        filtered_results = []
        minimum_seeders = tryInt(Env.setting('minimum_seeders', section = 'torrent', default = 1))

        # Filter out ignored and other releases we don't want
        for rel in results:

            if rel['status'] in ['ignored', 'failed']:
                log.info('Ignored: %s', rel['name'])
                continue

            if rel['score'] < quality_custom.get('minimum_score'):
                log.info('Ignored, score "%s" too low, need at least "%s": %s', (rel['score'], quality_custom.get('minimum_score'), rel['name']))
                continue

            if rel['size'] <= 50:
                log.info('Ignored, size "%sMB" too low: %s', (rel['size'], rel['name']))
                continue

            if 'seeders' in rel and rel.get('seeders') < minimum_seeders:
                log.info('Ignored, not enough seeders, has %s needs %s: %s', (rel.get('seeders'), minimum_seeders, rel['name']))
                continue

            # If a single release comes through the "wait for", let through all
            rel['wait_for'] = False
            if quality_custom.get('index') != 0 and quality_custom.get('wait_for', 0) > 0 and rel.get('age') <= quality_custom.get('wait_for', 0):
                rel['wait_for'] = True
            else:
                let_through = True

            filtered_results.append(rel)

        # Loop through filtered results
        for rel in filtered_results:

            # Only wait if not a single release is old enough
            if rel.get('wait_for') and not let_through:
                log.info('Ignored, waiting %s days: %s', (quality_custom.get('wait_for') - rel.get('age'), rel['name']))
                wait_for = True
                continue

            downloaded = fireEvent('release.download', data = rel, media = media, single = True)
            if downloaded is True:
                return True
            elif downloaded != 'try_next':
                break

        return wait_for

    def createFromSearch(self, search_results, media, quality):

        try:
            db = get_db()

            found_releases = []

            is_3d = False
            try: is_3d = quality['custom']['3d']
            except: pass

            for rel in search_results:

                rel_identifier = md5(rel['url'])

                release = {
                    '_t': 'release',
                    'identifier': rel_identifier,
                    'media_id': media.get('_id'),
                    'quality': quality.get('identifier'),
                    'is_3d': is_3d,
                    'status': rel.get('status', 'available'),
                    'last_edit': int(time.time()),
                    'info': {}
                }

                # Add downloader info if provided
                try:
                    release['download_info'] = rel['download_info']
                    del rel['download_info']
                except:
                    pass

                try:
                    rls = db.get('release_identifier', rel_identifier, with_doc = True)['doc']
                except:
                    rls = db.insert(release)
                    rls.update(release)

                # Update info, but filter out functions
                for info in rel:
                    try:
                        if not isinstance(rel[info], (str, unicode, int, long, float)):
                            continue

                        rls['info'][info] = toUnicode(rel[info]) if isinstance(rel[info], (str, unicode)) else rel[info]
                    except:
                        log.debug('Couldn\'t add %s to ReleaseInfo: %s', (info, traceback.format_exc()))

                db.update(rls)

                # Update release in search_results
                rel['status'] = rls.get('status')

                if rel['status'] == 'available':
                    found_releases.append(rel_identifier)

            return found_releases
        except:
            log.error('Failed: %s', traceback.format_exc())

        return []

    def updateStatus(self, release_id, status = None):
        if not status: return False

        try:
            db = get_db()

            rel = db.get('id', release_id)
            if rel and rel.get('status') != status:

                release_name = None
                if rel.get('files'):
                    for file_type in rel.get('files', {}):
                        if file_type == 'movie':
                            for release_file in rel['files'][file_type]:
                                release_name = os.path.basename(release_file)
                                break

                if not release_name and rel.get('info'):
                    release_name = rel['info'].get('name')

                #update status in Db
                log.debug('Marking release %s as %s', (release_name, status))
                rel['status'] = status
                rel['last_edit'] = int(time.time())

                db.update(rel)

                #Update all movie info as there is no release update function
                fireEvent('notify.frontend', type = 'release.update_status', data = rel)

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False

    def withStatus(self, status, with_doc = True):

        db = get_db()

        status = list(status if isinstance(status, (list, tuple)) else [status])

        for s in status:
            for ms in db.get_many('release_status', s):
                if with_doc:
                    try:
                        doc = db.get('id', ms['_id'])
                        yield doc
                    except RecordNotFound:
                        log.debug('Record not found, skipping: %s', ms['_id'])
                else:
                    yield ms

    def forMedia(self, media_id):

        db = get_db()
        raw_releases = db.get_many('release', media_id)

        releases = []
        for r in raw_releases:
            try:
                doc = db.get('id', r.get('_id'))
                releases.append(doc)
            except RecordDeleted:
                pass
            except (ValueError, EOFError):
                fireEvent('database.delete_corrupted', r.get('_id'), traceback_error = traceback.format_exc(0))

        releases = sorted(releases, key = lambda k: k.get('info', {}).get('score', 0), reverse = True)

        # Sort based on preferred search method
        download_preference = self.conf('preferred_method', section = 'searcher')
        if download_preference != 'both':
            releases = sorted(releases, key = lambda k: k.get('info', {}).get('protocol', '')[:3], reverse = (download_preference == 'torrent'))

        return releases or []
