from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import toUnicode, ss
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.helpers.variable import getExt, mergeDicts, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, File, Profile, Release
from couchpotato.environment import Env
import errno
import os
import re
import shutil
import traceback

log = CPLog(__name__)


class Renamer(Plugin):

    renaming_started = False

    def __init__(self):

        addApiView('renamer.scan', self.scanView, docs = {
            'desc': 'For the renamer to check for new files to rename',
        })

        addEvent('renamer.scan', self.scan)
        addEvent('renamer.check_snatched', self.checkSnatched)

        addEvent('app.load', self.scan)

        fireEvent('schedule.interval', 'renamer.check_snatched', self.checkSnatched, minutes = self.conf('run_every'))

    def scanView(self):

        fireEventAsync('renamer.scan')

        return jsonified({
            'success': True
        })

    def scan(self):

        if self.isDisabled():
            return

        if self.renaming_started is True:
            log.info('Renamer is disabled to avoid infinite looping of the same error.')
            return

        # Check to see if the "to" folder is inside the "from" folder.
        if not os.path.isdir(self.conf('from')) or not os.path.isdir(self.conf('to')):
            log.debug('"To" and "From" have to exist.')
            return
        elif self.conf('from') in self.conf('to'):
            log.error('The "to" can\'t be inside of the "from" folder. You\'ll get an infinite loop.')
            return

        groups = fireEvent('scanner.scan', folder = self.conf('from'), single = True)

        self.renaming_started = True

        destination = self.conf('to')
        folder_name = self.conf('folder_name')
        file_name = self.conf('file_name')
        trailer_name = self.conf('trailer_name')
        nfo_name = self.conf('nfo_name')
        separator = self.conf('separator')

        # Statusses
        done_status = fireEvent('status.get', 'done', single = True)
        active_status = fireEvent('status.get', 'active', single = True)
        downloaded_status = fireEvent('status.get', 'downloaded', single = True)
        snatched_status = fireEvent('status.get', 'snatched', single = True)

        db = get_session()

        for group_identifier in groups:

            group = groups[group_identifier]
            rename_files = {}
            remove_files = []
            remove_releases = []

            movie_title = getTitle(group['library'])

            # Add _UNKNOWN_ if no library item is connected
            if not group['library'] or not movie_title:
                self.tagDir(group, 'unknown')
                continue
            # Rename the files using the library data
            else:
                group['library'] = fireEvent('library.update', identifier = group['library']['identifier'], single = True)
                if not group['library']:
                    log.error('Could not rename, no library item to work with: %s', group_identifier)
                    continue

                library = group['library']
                movie_title = getTitle(library)

                # Find subtitle for renaming
                fireEvent('renamer.before', group)

                # Remove weird chars from moviename
                movie_name = re.sub(r"[\x00\/\\:\*\?\"<>\|]", '', movie_title)

                # Put 'The' at the end
                name_the = movie_name
                if movie_name[:4].lower() == 'the ':
                    name_the = movie_name[4:] + ', The'

                replacements = {
                     'ext': 'mkv',
                     'namethe': name_the.strip(),
                     'thename': movie_name.strip(),
                     'year': library['year'],
                     'first': name_the[0].upper(),
                     'quality': group['meta_data']['quality']['label'],
                     'quality_type': group['meta_data']['quality_type'],
                     'video': group['meta_data'].get('video'),
                     'audio': group['meta_data'].get('audio'),
                     'group': group['meta_data']['group'],
                     'source': group['meta_data']['source'],
                     'resolution_width': group['meta_data'].get('resolution_width'),
                     'resolution_height': group['meta_data'].get('resolution_height'),
                     'imdb_id': library['identifier'],
                }

                for file_type in group['files']:

                    # Move nfo depending on settings
                    if file_type is 'nfo' and not self.conf('rename_nfo'):
                        log.debug('Skipping, renaming of %s disabled', file_type)
                        if self.conf('cleanup'):
                            for current_file in group['files'][file_type]:
                                remove_files.append(current_file)
                        continue

                    # Subtitle extra
                    if file_type is 'subtitle_extra':
                        continue

                    # Move other files
                    multiple = len(group['files']['movie']) > 1 and not group['is_dvd']
                    cd = 1 if multiple else 0

                    for current_file in sorted(list(group['files'][file_type])):

                        # Original filename
                        replacements['original'] = os.path.splitext(os.path.basename(current_file))[0]
                        replacements['original_folder'] = fireEvent('scanner.remove_cptag', group['dirname'], single = True)

                        # Extension
                        replacements['ext'] = getExt(current_file)

                        # cd #
                        replacements['cd'] = ' cd%d' % cd if cd else ''
                        replacements['cd_nr'] = cd

                        # Naming
                        final_folder_name = self.doReplace(folder_name, replacements)
                        final_file_name = self.doReplace(file_name, replacements)
                        replacements['filename'] = final_file_name[:-(len(getExt(final_file_name)) + 1)]

                        # Group filename without cd extension
                        replacements['cd'] = ''
                        replacements['cd_nr'] = ''

                        # Meta naming
                        if file_type is 'trailer':
                            final_file_name = self.doReplace(trailer_name, replacements)
                        elif file_type is 'nfo':
                            final_file_name = self.doReplace(nfo_name, replacements)

                        # Seperator replace
                        if separator:
                            final_file_name = final_file_name.replace(' ', separator)

                        # Move DVD files (no structure renaming)
                        if group['is_dvd'] and file_type is 'movie':
                            found = False
                            for top_dir in ['video_ts', 'audio_ts', 'bdmv', 'certificate']:
                                has_string = current_file.lower().find(os.path.sep + top_dir + os.path.sep)
                                if has_string >= 0:
                                    structure_dir = current_file[has_string:].lstrip(os.path.sep)
                                    rename_files[current_file] = os.path.join(destination, final_folder_name, structure_dir)
                                    found = True
                                    break

                            if not found:
                                log.error('Could not determine dvd structure for: %s', current_file)

                        # Do rename others
                        else:
                            if file_type is 'leftover':
                                if self.conf('move_leftover'):
                                    rename_files[current_file] = os.path.join(destination, final_folder_name, os.path.basename(current_file))
                            elif file_type not in ['subtitle']:
                                rename_files[current_file] = os.path.join(destination, final_folder_name, final_file_name)

                        # Check for extra subtitle files
                        if file_type is 'subtitle':

                            # rename subtitles with or without language
                            rename_files[current_file] = os.path.join(destination, final_folder_name, final_file_name)
                            sub_langs = group['subtitle_language'].get(current_file, [])

                            rename_extras = self.getRenameExtras(
                                extra_type = 'subtitle_extra',
                                replacements = replacements,
                                folder_name = folder_name,
                                file_name = file_name,
                                destination = destination,
                                group = group,
                                current_file = current_file
                            )

                            # Don't add language if multiple languages in 1 file
                            if len(sub_langs) > 1:
                                rename_files[current_file] = os.path.join(destination, final_folder_name, final_file_name)
                            elif len(sub_langs) == 1:
                                sub_name = final_file_name.replace(replacements['ext'], '%s.%s' % (sub_langs[0], replacements['ext']))
                                rename_files[current_file] = os.path.join(destination, final_folder_name, sub_name)

                            rename_files = mergeDicts(rename_files, rename_extras)

                        # Filename without cd etc
                        if file_type is 'movie':
                            rename_extras = self.getRenameExtras(
                                extra_type = 'movie_extra',
                                replacements = replacements,
                                folder_name = folder_name,
                                file_name = file_name,
                                destination = destination,
                                group = group,
                                current_file = current_file
                            )
                            rename_files = mergeDicts(rename_files, rename_extras)

                            group['filename'] = self.doReplace(file_name, replacements)[:-(len(getExt(final_file_name)) + 1)]
                            group['destination_dir'] = os.path.join(destination, final_folder_name)

                        if multiple:
                            cd += 1

                # Before renaming, remove the lower quality files
                library = db.query(Library).filter_by(identifier = group['library']['identifier']).first()
                remove_leftovers = True

                # Add it to the wanted list before we continue
                if len(library.movies) == 0:
                    profile = db.query(Profile).filter_by(core = True, label = group['meta_data']['quality']['label']).first()
                    fireEvent('movie.add', params = {'identifier': group['library']['identifier'], 'profile_id': profile.id}, search_after = False)
                    db.expire_all()
                    library = db.query(Library).filter_by(identifier = group['library']['identifier']).first()

                for movie in library.movies:

                    # Mark movie "done" onces it found the quality with the finish check
                    try:
                        if movie.status_id == active_status.get('id') and movie.profile:
                            for profile_type in movie.profile.types:
                                if profile_type.quality_id == group['meta_data']['quality']['id'] and profile_type.finish:
                                    movie.status_id = done_status.get('id')
                                    db.commit()
                    except Exception, e:
                        log.error('Failed marking movie finished: %s %s', (e, traceback.format_exc()))

                    # Go over current movie releases
                    for release in movie.releases:

                        # When a release already exists
                        if release.status_id is done_status.get('id'):

                            # This is where CP removes older, lesser quality releases
                            if release.quality.order > group['meta_data']['quality']['order']:
                                log.info('Removing lesser quality %s for %s.', (movie.library.titles[0].title, release.quality.label))
                                for current_file in release.files:
                                    remove_files.append(current_file)
                                remove_releases.append(release)
                            # Same quality, but still downloaded, so maybe repack/proper/unrated/directors cut etc
                            elif release.quality.order is group['meta_data']['quality']['order']:
                                log.info('Same quality release already exists for %s, with quality %s. Assuming repack.', (movie.library.titles[0].title, release.quality.label))
                                for current_file in release.files:
                                    remove_files.append(current_file)
                                remove_releases.append(release)

                            # Downloaded a lower quality, rename the newly downloaded files/folder to exclude them from scan
                            else:
                                log.info('Better quality release already exists for %s, with quality %s', (movie.library.titles[0].title, release.quality.label))

                                # Add _EXISTS_ to the parent dir
                                self.tagDir(group, 'exists')

                                # Notify on rename fail
                                download_message = 'Renaming of %s (%s) canceled, exists in %s already.' % (movie.library.titles[0].title, group['meta_data']['quality']['label'], release.quality.label)
                                fireEvent('movie.renaming.canceled', message = download_message, data = group)
                                remove_leftovers = False

                                break
                        elif release.status_id is snatched_status.get('id'):
                            if release.quality.id is group['meta_data']['quality']['id']:
                                log.debug('Marking release as downloaded')
                                release.status_id = downloaded_status.get('id')
                                db.commit()

                # Remove leftover files
                if self.conf('cleanup') and not self.conf('move_leftover') and remove_leftovers:
                    log.debug('Removing leftover files')
                    for current_file in group['files']['leftover']:
                        remove_files.append(current_file)
                elif not remove_leftovers: # Don't remove anything
                    break

            # Remove files
            delete_folders = []
            for src in remove_files:

                if isinstance(src, File):
                    src = src.path

                if rename_files.get(src):
                    log.debug('Not removing file that will be renamed: %s', src)
                    continue

                log.info('Removing "%s"', src)
                try:
                    if os.path.isfile(src):
                        os.remove(src)

                        parent_dir = os.path.normpath(os.path.dirname(src))
                        if delete_folders.count(parent_dir) == 0 and os.path.isdir(parent_dir) and destination != parent_dir:
                            delete_folders.append(parent_dir)

                except:
                    log.error('Failed removing %s: %s', (src, traceback.format_exc()))
                    self.tagDir(group, 'failed_remove')

            # Delete leftover folder from older releases
            for delete_folder in delete_folders:
                self.deleteEmptyFolder(delete_folder, show_error = False)

            # Rename all files marked
            group['renamed_files'] = []
            for src in rename_files:
                if rename_files[src]:
                    dst = rename_files[src]
                    log.info('Renaming "%s" to "%s"', (src, dst))

                    # Create dir
                    self.makeDir(os.path.dirname(dst))

                    try:
                        self.moveFile(src, dst)
                        group['renamed_files'].append(dst)
                    except:
                        log.error('Failed moving the file "%s" : %s', (os.path.basename(src), traceback.format_exc()))
                        self.tagDir(group, 'failed_rename')

            # Remove matching releases
            for release in remove_releases:
                log.debug('Removing release %s', release.identifier)
                try:
                    db.delete(release)
                except:
                    log.error('Failed removing %s: %s', (release.identifier, traceback.format_exc()))

            if group['dirname'] and group['parentdir']:
                try:
                    log.info('Deleting folder: %s', group['parentdir'])
                    self.deleteEmptyFolder(group['parentdir'])
                except:
                    log.error('Failed removing %s: %s', (group['parentdir'], traceback.format_exc()))

            # Search for trailers etc
            fireEventAsync('renamer.after', group)

            # Notify on download
            download_message = 'Downloaded %s (%s)' % (movie_title, replacements['quality'])
            fireEventAsync('movie.downloaded', message = download_message, data = group)

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        #db.close()
        self.renaming_started = False

    def getRenameExtras(self, extra_type = '', replacements = {}, folder_name = '', file_name = '', destination = '', group = {}, current_file = ''):

        rename_files = {}

        def test(s):
            return current_file[:-len(replacements['ext'])] in s

        for extra in set(filter(test, group['files'][extra_type])):
            replacements['ext'] = getExt(extra)

            final_folder_name = self.doReplace(folder_name, replacements)
            final_file_name = self.doReplace(file_name, replacements)
            rename_files[extra] = os.path.join(destination, final_folder_name, final_file_name)

        return rename_files

    def tagDir(self, group, tag):

        rename_files = {}

        if group['dirname']:
            rename_files[group['parentdir']] = group['parentdir'].replace(group['dirname'], '_%s_%s' % (tag.upper(), group['dirname']))
        else: # Add it to filename
            for file_type in group['files']:
                for rename_me in group['files'][file_type]:
                    filename = os.path.basename(rename_me)
                    rename_files[rename_me] = rename_me.replace(filename, '_%s_%s' % (tag.upper(), filename))

        for src in rename_files:
            if rename_files[src]:
                dst = rename_files[src]
                log.info('Renaming "%s" to "%s"', (src, dst))

                # Create dir
                self.makeDir(os.path.dirname(dst))

                try:
                    self.moveFile(src, dst)
                except:
                    log.error('Failed moving the file "%s" : %s', (os.path.basename(src), traceback.format_exc()))
                    raise

    def moveFile(self, old, dest):
        dest = ss(dest)
        try:
            shutil.move(old, dest)

            try:
                os.chmod(dest, Env.getPermission('file'))
            except:
                log.error('Failed setting permissions for file: %s, %s', (dest, traceback.format_exc(1)))

        except OSError, err:
            # Copying from a filesystem with octal permission to an NTFS file system causes a permission error.  In this case ignore it.
            if not hasattr(os, 'chmod') or err.errno != errno.EPERM:
                raise
            else:
                if os.path.exists(dest):
                    os.unlink(old)

        except:
            log.error('Couldn\'t move file "%s" to "%s": %s', (old, dest, traceback.format_exc()))
            raise Exception

        return True

    def doReplace(self, string, replacements):
        '''
        replace confignames with the real thing
        '''

        replaced = toUnicode(string)
        for x, r in replacements.iteritems():
            if r is not None:
                replaced = replaced.replace(u'<%s>' % toUnicode(x), toUnicode(r))
            else:
                #If information is not available, we don't want the tag in the filename
                replaced = replaced.replace('<' + x + '>', '')

        replaced = re.sub(r"[\x00:\*\?\"<>\|]", '', replaced)

        sep = self.conf('separator')
        return self.replaceDoubles(replaced).replace(' ', ' ' if not sep else sep)

    def replaceDoubles(self, string):
        return string.replace('  ', ' ').replace(' .', '.')

    def deleteEmptyFolder(self, folder, show_error = True):

        loge = log.error if show_error else log.debug
        for root, dirs, files in os.walk(folder):

            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                if len(os.listdir(full_path)) == 0:
                    try:
                        os.rmdir(full_path)
                    except:
                        loge('Couldn\'t remove empty directory %s: %s', (full_path, traceback.format_exc()))

        try:
            os.rmdir(folder)
        except:
            loge('Couldn\'t remove empty directory %s: %s', (folder, traceback.format_exc()))

    def checkSnatched(self):
        snatched_status = fireEvent('status.get', 'snatched', single = True)
        ignored_status = fireEvent('status.get', 'ignored', single = True)
        failed_status = fireEvent('status.get', 'failed', single = True)

        done_status = fireEvent('status.get', 'done', single = True)

        db = get_session()
        rels = db.query(Release).filter_by(status_id = snatched_status.get('id')).all()

        if rels:
            log.debug('Checking status snatched releases...')

        scan_required = False

        for rel in rels:

            # Get current selected title
            default_title = ''
            for title in rel.movie.library.titles:
                if title.default: default_title = title.title

            # Check if movie has already completed and is manage tab (legacy db correction)
            if rel.movie.status_id == done_status.get('id'):
                log.debug('Found a completed movie with a snatched release : %s. Setting release status to ignored...' , default_title)
                rel.status_id = ignored_status.get('id')
                db.commit()
                continue

            item = {}
            for info in rel.info:
                item[info.identifier] = info.value

            movie_dict = fireEvent('movie.get', rel.movie_id, single = True)

            # check status
            downloadstatus = fireEvent('download.status', data = item, movie = movie_dict, single = True)
            if not downloadstatus:
                log.debug('Download status functionality is not implemented for active downloaders.')
                scan_required = True
            else:
                log.debug('Download status: %s' , downloadstatus)

                if downloadstatus == 'failed':
                    if self.conf('next_on_failed'):
                        fireEvent('searcher.try_next_release', movie_id = rel.movie_id)
                    else:
                        rel.status_id = failed_status.get('id')
                        db.commit()

                        log.info('Download of %s failed.', item['name'])

                elif downloadstatus == 'completed':
                    log.info('Download of %s completed!', item['name'])
                    scan_required = True

                elif downloadstatus == 'not_found':
                    log.info('%s not found in downloaders', item['name'])
                    rel.status_id = ignored_status.get('id')
                    db.commit()

        # Note that Queued, Downloading, Paused, Repair and Unpackimg are also available as status for SabNZBd
        if scan_required:
            fireEvent('renamer.scan')
