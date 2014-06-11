import fnmatch
import os
import re
import shutil
import time
import traceback

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import toUnicode, ss, sp
from couchpotato.core.helpers.variable import getExt, mergeDicts, getTitle, \
    getImdb, link, symlink, tryInt, splitString, fnEscape, isSubFolder, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from unrar2 import RarFile
import six
from six.moves import filter


log = CPLog(__name__)

autoload = 'Renamer'


class Renamer(Plugin):

    renaming_started = False
    checking_snatched = False

    def __init__(self):
        addApiView('renamer.scan', self.scanView, docs = {
            'desc': 'For the renamer to check for new files to rename in a folder',
            'params': {
                'async': {'desc': 'Optional: Set to 1 if you dont want to fire the renamer.scan asynchronous.'},
                'media_folder': {'desc': 'Optional: The folder of the media to scan. Keep empty for default renamer folder.'},
                'files': {'desc': 'Optional: Provide the release files if more releases are in the same media_folder, delimited with a \'|\'. Note that no dedicated release folder is expected for releases with one file.'},
                'base_folder': {'desc': 'Optional: The folder to find releases in. Leave empty for default folder.'},
                'downloader': {'desc': 'Optional: The downloader the release has been downloaded with. \'download_id\' is required with this option.'},
                'download_id': {'desc': 'Optional: The nzb/torrent ID of the release in media_folder. \'downloader\' is required with this option.'},
                'status': {'desc': 'Optional: The status of the release: \'completed\' (default) or \'seeding\''},
            },
        })

        addEvent('renamer.scan', self.scan)
        addEvent('renamer.check_snatched', self.checkSnatched)

        addEvent('app.load', self.scan)
        addEvent('app.load', self.setCrons)

        # Enable / disable interval
        addEvent('setting.save.renamer.enabled.after', self.setCrons)
        addEvent('setting.save.renamer.run_every.after', self.setCrons)
        addEvent('setting.save.renamer.force_every.after', self.setCrons)

    def setCrons(self):

        fireEvent('schedule.remove', 'renamer.check_snatched')
        if self.isEnabled() and self.conf('run_every') > 0:
            fireEvent('schedule.interval', 'renamer.check_snatched', self.checkSnatched, minutes = self.conf('run_every'), single = True)

        fireEvent('schedule.remove', 'renamer.check_snatched_forced')
        if self.isEnabled() and self.conf('force_every') > 0:
            fireEvent('schedule.interval', 'renamer.check_snatched_forced', self.scan, hours = self.conf('force_every'), single = True)

        return True

    def scanView(self, **kwargs):

        async = tryInt(kwargs.get('async', 0))
        base_folder = kwargs.get('base_folder')
        media_folder = sp(kwargs.get('media_folder'))

        # Backwards compatibility, to be removed after a few versions :)
        if not media_folder:
            media_folder = sp(kwargs.get('movie_folder'))

        downloader = kwargs.get('downloader')
        download_id = kwargs.get('download_id')
        files = [sp(filename) for filename in splitString(kwargs.get('files'), '|')]
        status = kwargs.get('status', 'completed')

        release_download = None
        if not base_folder and media_folder:
            release_download = {'folder': media_folder}

            if download_id:
                release_download.update({
                    'id': download_id,
                    'downloader': downloader,
                    'status': status,
                    'files': files
                })

        fire_handle = fireEvent if not async else fireEventAsync
        fire_handle('renamer.scan', base_folder = base_folder, release_download = release_download)

        return {
            'success': True
        }

    def scan(self, base_folder = None, release_download = None):
        if not release_download: release_download = {}

        if self.isDisabled():
            return

        if self.renaming_started is True:
            log.info('Renamer is already running, if you see this often, check the logs above for errors.')
            return

        if not base_folder:
            base_folder = sp(self.conf('from'))

        from_folder = sp(self.conf('from'))
        to_folder = sp(self.conf('to'))

        # Get media folder to process
        media_folder = sp(release_download.get('folder'))

        # Get all folders that should not be processed
        no_process = [to_folder]
        cat_list = fireEvent('category.all', single = True) or []
        no_process.extend([item['destination'] for item in cat_list])
        try:
            if Env.setting('library', section = 'manage').strip():
                no_process.extend([sp(manage_folder) for manage_folder in splitString(Env.setting('library', section = 'manage'), '::')])
        except:
            pass

        # Check to see if the no_process folders are inside the "from" folder.
        if not os.path.isdir(base_folder) or not os.path.isdir(to_folder):
            log.error('Both the "To" and "From" folder have to exist.')
            return
        else:
            for item in no_process:
                if isSubFolder(item, base_folder):
                    log.error('To protect your data, the media libraries can\'t be inside of or the same as the "from" folder.')
                    return

        # Check to see if the no_process folders are inside the provided media_folder
        if media_folder and not os.path.isdir(media_folder):
            log.debug('The provided media folder %s does not exist. Trying to find it in the \'from\' folder.', media_folder)

            # Update to the from folder
            if len(release_download.get('files', [])) == 1:
                new_media_folder = sp(from_folder)
            else:
                new_media_folder = sp(os.path.join(from_folder, os.path.basename(media_folder)))

            if not os.path.isdir(new_media_folder):
                log.error('The provided media folder %s does not exist and could also not be found in the \'from\' folder.', media_folder)
                return

            # Update the files
            new_files = [os.path.join(new_media_folder, os.path.relpath(filename, media_folder)) for filename in release_download.get('files', [])]
            if new_files and not os.path.isfile(new_files[0]):
                log.error('The provided media folder %s does not exist and its files could also not be found in the \'from\' folder.', media_folder)
                return

            # Update release_download info to the from folder
            log.debug('Release %s found in the \'from\' folder.', media_folder)
            release_download['folder'] = new_media_folder
            release_download['files'] = new_files
            media_folder = new_media_folder

        if media_folder:
            for item in no_process:
                if isSubFolder(item, media_folder):
                    log.error('To protect your data, the media libraries can\'t be inside of or the same as the provided media folder.')
                    return

        # Make sure a checkSnatched marked all downloads/seeds as such
        if not release_download and self.conf('run_every') > 0:
            self.checkSnatched(fire_scan = False)

        self.renaming_started = True

        # make sure the media folder name is included in the search
        folder = None
        files = []
        if media_folder:
            log.info('Scanning media folder %s...', media_folder)
            folder = os.path.dirname(media_folder)

            release_files = release_download.get('files', [])
            if release_files:
                files = release_files

                # If there is only one file in the torrent, the downloader did not create a subfolder
                if len(release_files) == 1:
                    folder = media_folder
            else:
                # Get all files from the specified folder
                try:
                    for root, folders, names in os.walk(media_folder):
                        files.extend([sp(os.path.join(root, name)) for name in names])
                except:
                    log.error('Failed getting files from %s: %s', (media_folder, traceback.format_exc()))

        db = get_db()

        # Extend the download info with info stored in the downloaded release
        if release_download:
            release_download = self.extendReleaseDownload(release_download)

        # Unpack any archives
        extr_files = None
        if self.conf('unrar'):
            folder, media_folder, files, extr_files = self.extractFiles(folder = folder, media_folder = media_folder, files = files,
                                                                        cleanup = self.conf('cleanup') and not self.downloadIsTorrent(release_download))

        groups = fireEvent('scanner.scan', folder = folder if folder else base_folder,
                           files = files, release_download = release_download, return_ignored = False, single = True) or []

        folder_name = self.conf('folder_name')
        file_name = self.conf('file_name')
        trailer_name = self.conf('trailer_name')
        nfo_name = self.conf('nfo_name')
        separator = self.conf('separator')

        # Tag release folder as failed_rename in case no groups were found. This prevents check_snatched from removing the release from the downloader.
        if not groups and self.statusInfoComplete(release_download):
            self.tagRelease(release_download = release_download, tag = 'failed_rename')

        for group_identifier in groups:

            group = groups[group_identifier]
            group['release_download'] = None
            rename_files = {}
            remove_files = []
            remove_releases = []

            media_title = getTitle(group)

            # Add _UNKNOWN_ if no library item is connected
            if not group.get('media') or not media_title:
                self.tagRelease(group = group, tag = 'unknown')
                continue
            # Rename the files using the library data
            else:

                # Media not in library, add it first
                if not group['media'].get('_id'):
                    group['media'] = fireEvent('movie.add', params = {
                        'identifier': group['identifier'],
                        'profile_id': None
                    }, search_after = False, status = 'done', single = True)
                else:
                    group['media'] = fireEvent('movie.update_info', media_id = group['media'].get('_id'), single = True)

                if not group['media'] or not group['media'].get('_id'):
                    log.error('Could not rename, no library item to work with: %s', group_identifier)
                    continue

                media = group['media']
                media_title = getTitle(media)

                # Overwrite destination when set in category
                destination = to_folder
                category_label = ''

                if media.get('category_id') and media.get('category_id') != '-1':
                    try:
                        category = db.get('id', media['category_id'])
                        category_label = category['label']

                        if category['destination'] and len(category['destination']) > 0 and category['destination'] != 'None':
                            destination = category['destination']
                            log.debug('Setting category destination for "%s": %s' % (media_title, destination))
                        else:
                            log.debug('No category destination found for "%s"' % media_title)
                    except:
                        log.error('Failed getting category label: %s', traceback.format_exc())

                # Find subtitle for renaming
                group['before_rename'] = []
                fireEvent('renamer.before', group)

                # Add extracted files to the before_rename list
                if extr_files:
                    group['before_rename'].extend(extr_files)

                # Remove weird chars from movie name
                movie_name = re.sub(r"[\x00\/\\:\*\?\"<>\|]", '', media_title)

                # Put 'The' at the end
                name_the = movie_name
                for prefix in ['the ', 'an ', 'a ']:
                    if prefix == movie_name[:len(prefix)].lower():
                        name_the = movie_name[len(prefix):] + ', ' + prefix.strip().capitalize()
                        break

                replacements = {
                    'ext': 'mkv',
                    'namethe': name_the.strip(),
                    'thename': movie_name.strip(),
                    'year': media['info']['year'],
                    'first': name_the[0].upper(),
                    'quality': group['meta_data']['quality']['label'],
                    'quality_type': group['meta_data']['quality_type'],
                    'video': group['meta_data'].get('video'),
                    'audio': group['meta_data'].get('audio'),
                    'group': group['meta_data']['group'],
                    'source': group['meta_data']['source'],
                    'resolution_width': group['meta_data'].get('resolution_width'),
                    'resolution_height': group['meta_data'].get('resolution_height'),
                    'audio_channels': group['meta_data'].get('audio_channels'),
                    'imdb_id': group['identifier'],
                    'cd': '',
                    'cd_nr': '',
                    'mpaa': media['info'].get('mpaa', ''),
                    'mpaa_only': media['info'].get('mpaa', ''),
                    'category': category_label,
                    '3d': '3D' if group['meta_data']['quality'].get('is_3d', 0) else '',
                    '3d_type': group['meta_data'].get('3d_type'),
                }

                if replacements['mpaa_only'] not in ('G', 'PG', 'PG-13', 'R', 'NC-17'):
                    replacements['mpaa_only'] = 'Not Rated'

                for file_type in group['files']:

                    # Move nfo depending on settings
                    if file_type is 'nfo' and not self.conf('rename_nfo'):
                        log.debug('Skipping, renaming of %s disabled', file_type)
                        for current_file in group['files'][file_type]:
                            if self.conf('cleanup') and (not self.downloadIsTorrent(release_download) or self.fileIsAdded(current_file, group)):
                                remove_files.append(current_file)
                        continue

                    # Subtitle extra
                    if file_type is 'subtitle_extra':
                        continue

                    # Move other files
                    multiple = len(group['files'][file_type]) > 1 and not group['is_dvd']
                    cd = 1 if multiple else 0

                    for current_file in sorted(list(group['files'][file_type])):
                        current_file = sp(current_file)

                        # Original filename
                        replacements['original'] = os.path.splitext(os.path.basename(current_file))[0]
                        replacements['original_folder'] = fireEvent('scanner.remove_cptag', group['dirname'], single = True)

                        # Extension
                        replacements['ext'] = getExt(current_file)

                        # cd #
                        replacements['cd'] = ' cd%d' % cd if multiple else ''
                        replacements['cd_nr'] = cd if multiple else ''

                        # Naming
                        final_folder_name = self.doReplace(folder_name, replacements, folder = True)
                        final_file_name = self.doReplace(file_name, replacements)
                        replacements['filename'] = final_file_name[:-(len(getExt(final_file_name)) + 1)]

                        # Meta naming
                        if file_type is 'trailer':
                            final_file_name = self.doReplace(trailer_name, replacements, remove_multiple = True)
                        elif file_type is 'nfo':
                            final_file_name = self.doReplace(nfo_name, replacements, remove_multiple = True)

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

                            remove_multiple = False
                            if len(group['files']['movie']) == 1:
                                remove_multiple = True

                            sub_langs = group['subtitle_language'].get(current_file, [])

                            # rename subtitles with or without language
                            sub_name = self.doReplace(file_name, replacements, remove_multiple = remove_multiple)
                            rename_files[current_file] = os.path.join(destination, final_folder_name, sub_name)

                            rename_extras = self.getRenameExtras(
                                extra_type = 'subtitle_extra',
                                replacements = replacements,
                                folder_name = folder_name,
                                file_name = file_name,
                                destination = destination,
                                group = group,
                                current_file = current_file,
                                remove_multiple = remove_multiple,
                            )

                            # Don't add language if multiple languages in 1 subtitle file
                            if len(sub_langs) == 1:
                                sub_suffix = '%s.%s' % (sub_langs[0], replacements['ext'])

                                # Don't add language to subtitle file it it's already there
                                if not sub_name.endswith(sub_suffix):
                                    sub_name = sub_name.replace(replacements['ext'], sub_suffix)
                                    rename_files[current_file] = os.path.join(destination, final_folder_name, sub_name)

                            rename_files = mergeDicts(rename_files, rename_extras)

                        # Filename without cd etc
                        elif file_type is 'movie':
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

                            group['filename'] = self.doReplace(file_name, replacements, remove_multiple = True)[:-(len(getExt(final_file_name)) + 1)]
                            group['destination_dir'] = os.path.join(destination, final_folder_name)

                        if multiple:
                            cd += 1

                # Before renaming, remove the lower quality files
                remove_leftovers = True

                # Mark movie "done" once it's found the quality with the finish check
                profile = None
                try:
                    if media.get('status') == 'active' and media.get('profile_id'):
                        profile = db.get('id', media['profile_id'])
                        if fireEvent('quality.isfinish', group['meta_data']['quality'], profile, single = True):
                            mdia = db.get('id', media['_id'])
                            mdia['status'] = 'done'
                            mdia['last_edit'] = int(time.time())
                            db.update(mdia)

                except:
                    log.error('Failed marking movie finished: %s', (traceback.format_exc()))

                # Go over current movie releases
                for release in fireEvent('release.for_media', media['_id'], single = True):

                    # When a release already exists
                    if release.get('status') == 'done':

                        # This is where CP removes older, lesser quality releases or releases that are not wanted anymore
                        is_higher = fireEvent('quality.ishigher', \
                            group['meta_data']['quality'], {'identifier': release['quality'], 'is_3d': release.get('is_3d', 0)}, profile, single = True)

                        if is_higher == 'higher':
                            log.info('Removing lesser or not wanted quality %s for %s.', (media_title, release.get('quality')))
                            for file_type in release.get('files', {}):
                                for release_file in release['files'][file_type]:
                                    remove_files.append(release_file)
                            remove_releases.append(release)

                        # Same quality, but still downloaded, so maybe repack/proper/unrated/directors cut etc
                        elif is_higher == 'equal':
                            log.info('Same quality release already exists for %s, with quality %s. Assuming repack.', (media_title, release.get('quality')))
                            for file_type in release.get('files', {}):
                                for release_file in release['files'][file_type]:
                                    remove_files.append(release_file)
                            remove_releases.append(release)

                        # Downloaded a lower quality, rename the newly downloaded files/folder to exclude them from scan
                        else:
                            log.info('Better quality release already exists for %s, with quality %s', (media_title, release.get('quality')))

                            # Add exists tag to the .ignore file
                            self.tagRelease(group = group, tag = 'exists')

                            # Notify on rename fail
                            download_message = 'Renaming of %s (%s) cancelled, exists in %s already.' % (media_title, group['meta_data']['quality']['label'], release.get('identifier'))
                            fireEvent('movie.renaming.canceled', message = download_message, data = group)
                            remove_leftovers = False

                            break

                    elif release.get('status') in ['snatched', 'seeding']:
                        if release_download and release_download.get('release_id'):
                            if release_download['release_id'] == release['_id']:
                                if release_download['status'] == 'completed':
                                    # Set the release to downloaded
                                    fireEvent('release.update_status', release['_id'], status = 'downloaded', single = True)
                                    group['release_download'] = release_download
                                elif release_download['status'] == 'seeding':
                                    # Set the release to seeding
                                    fireEvent('release.update_status', release['_id'], status = 'seeding', single = True)

                        elif release.get('identifier') == group['meta_data']['quality']['identifier']:
                            # Set the release to downloaded
                            fireEvent('release.update_status', release['_id'], status = 'downloaded', single = True)
                            group['release_download'] = release_download

                # Remove leftover files
                if not remove_leftovers:  # Don't remove anything
                    break

                log.debug('Removing leftover files')
                for current_file in group['files']['leftover']:
                    if self.conf('cleanup') and not self.conf('move_leftover') and \
                            (not self.downloadIsTorrent(release_download) or self.fileIsAdded(current_file, group)):
                        remove_files.append(current_file)

            # Remove files
            delete_folders = []
            for src in remove_files:

                if rename_files.get(src):
                    log.debug('Not removing file that will be renamed: %s', src)
                    continue

                log.info('Removing "%s"', src)
                try:
                    src = sp(src)
                    if os.path.isfile(src):
                        os.remove(src)

                        parent_dir = os.path.dirname(src)
                        if delete_folders.count(parent_dir) == 0 and os.path.isdir(parent_dir) and \
                                not isSubFolder(destination, parent_dir) and not isSubFolder(media_folder, parent_dir) and \
                                not isSubFolder(parent_dir, base_folder):

                            delete_folders.append(parent_dir)

                except:
                    log.error('Failed removing %s: %s', (src, traceback.format_exc()))
                    self.tagRelease(group = group, tag = 'failed_remove')

            # Delete leftover folder from older releases
            for delete_folder in delete_folders:
                try:
                    self.deleteEmptyFolder(delete_folder, show_error = False)
                except Exception as e:
                    log.error('Failed to delete folder: %s %s', (e, traceback.format_exc()))

            # Rename all files marked
            group['renamed_files'] = []
            failed_rename = False
            for src in rename_files:
                if rename_files[src]:
                    dst = rename_files[src]
                    log.info('Renaming "%s" to "%s"', (src, dst))

                    # Create dir
                    self.makeDir(os.path.dirname(dst))

                    try:
                        self.moveFile(src, dst, forcemove = not self.downloadIsTorrent(release_download) or self.fileIsAdded(src, group))
                        group['renamed_files'].append(dst)
                    except:
                        log.error('Failed renaming the file "%s" : %s', (os.path.basename(src), traceback.format_exc()))
                        failed_rename = True
                        break

            # If renaming failed tag the release folder as failed and continue with next group. Note that all old files have already been deleted.
            if failed_rename:
                self.tagRelease(group = group, tag = 'failed_rename')
                continue
            # If renaming succeeded, make sure it is not tagged as failed (scanner didn't return a group, but a download_ID was provided in an earlier attempt)
            else:
                self.untagRelease(group = group, tag = 'failed_rename')

            # Tag folder if it is in the 'from' folder and it will not be removed because it is a torrent
            if self.movieInFromFolder(media_folder) and self.downloadIsTorrent(release_download):
                self.tagRelease(group = group, tag = 'renamed_already')

            # Remove matching releases
            for release in remove_releases:
                log.debug('Removing release %s', release.get('identifier'))
                try:
                    db.delete(release)
                except:
                    log.error('Failed removing %s: %s', (release, traceback.format_exc()))

            if group['dirname'] and group['parentdir'] and not self.downloadIsTorrent(release_download):
                if media_folder:
                    # Delete the movie folder
                    group_folder = media_folder
                else:
                    # Delete the first empty subfolder in the tree relative to the 'from' folder
                    group_folder = sp(os.path.join(base_folder, os.path.relpath(group['parentdir'], base_folder).split(os.path.sep)[0]))

                try:
                    log.info('Deleting folder: %s', group_folder)
                    self.deleteEmptyFolder(group_folder)
                except:
                    log.error('Failed removing %s: %s', (group_folder, traceback.format_exc()))

            # Notify on download, search for trailers etc
            download_message = 'Downloaded %s (%s%s)' % (media_title, replacements['quality'], (' ' + replacements['3d']) if replacements['3d'] else '')
            try:
                fireEvent('renamer.after', message = download_message, group = group, in_order = True)
            except:
                log.error('Failed firing (some) of the renamer.after events: %s', traceback.format_exc())

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        self.renaming_started = False

    def getRenameExtras(self, extra_type = '', replacements = None, folder_name = '', file_name = '', destination = '', group = None, current_file = '', remove_multiple = False):
        if not group: group = {}
        if not replacements: replacements = {}

        replacements = replacements.copy()
        rename_files = {}

        def test(s):
            return current_file[:-len(replacements['ext'])] in sp(s)

        for extra in set(filter(test, group['files'][extra_type])):
            replacements['ext'] = getExt(extra)

            final_folder_name = self.doReplace(folder_name, replacements, remove_multiple = remove_multiple, folder = True)
            final_file_name = self.doReplace(file_name, replacements, remove_multiple = remove_multiple)
            rename_files[extra] = os.path.join(destination, final_folder_name, final_file_name)

        return rename_files

    # This adds a file to ignore / tag a release so it is ignored later
    def tagRelease(self, tag, group = None, release_download = None):
        if not tag:
            return

        text = """This file is from CouchPotato
It has marked this release as "%s"
This file hides the release from the renamer
Remove it if you want it to be renamed (again, or at least let it try again)
""" % tag

        tag_files = []

        # Tag movie files if they are known
        if isinstance(group, dict):
            tag_files = [sorted(list(group['files']['movie']))[0]]

        elif isinstance(release_download, dict):
            # Tag download_files if they are known
            if release_download.get('files', []):
                tag_files = [filename for filename in release_download.get('files', []) if os.path.exists(filename)]

            # Tag all files in release folder
            elif release_download['folder']:
                for root, folders, names in os.walk(sp(release_download['folder'])):
                    tag_files.extend([os.path.join(root, name) for name in names])

        for filename in tag_files:

            # Don't tag .ignore files
            if os.path.splitext(filename)[1] == '.ignore':
                continue

            tag_filename = '%s.%s.ignore' % (os.path.splitext(filename)[0], tag)
            if not os.path.isfile(tag_filename):
                self.createFile(tag_filename, text)

    def untagRelease(self, group = None, release_download = None, tag = ''):
        if not release_download:
            return

        tag_files = []
        folder = None

        # Tag movie files if they are known
        if isinstance(group, dict):
            tag_files = [sorted(list(group['files']['movie']))[0]]

            folder = sp(group['parentdir'])
            if not group.get('dirname') or not os.path.isdir(folder):
                return False

        elif isinstance(release_download, dict):

            folder = sp(release_download['folder'])
            if not os.path.isdir(folder):
                return False

            # Untag download_files if they are known
            if release_download.get('files'):
                tag_files = release_download.get('files', [])

            # Untag all files in release folder
            else:
                for root, folders, names in os.walk(folder):
                    tag_files.extend([sp(os.path.join(root, name)) for name in names if not os.path.splitext(name)[1] == '.ignore'])

        if not folder:
            return False

        # Find all .ignore files in folder
        ignore_files = []
        for root, dirnames, filenames in os.walk(folder):
            ignore_files.extend(fnmatch.filter([sp(os.path.join(root, filename)) for filename in filenames], '*%s.ignore' % tag))

        # Match all found ignore files with the tag_files and delete if found
        for tag_file in tag_files:
            ignore_file = fnmatch.filter(ignore_files, fnEscape('%s.%s.ignore' % (os.path.splitext(tag_file)[0], tag if tag else '*')))
            for filename in ignore_file:
                try:
                    os.remove(filename)
                except:
                    log.debug('Unable to remove ignore file: %s. Error: %s.' % (filename, traceback.format_exc()))

    def hastagRelease(self, release_download, tag = ''):
        if not release_download:
            return False

        folder = sp(release_download['folder'])
        if not os.path.isdir(folder):
            return False

        tag_files = []
        ignore_files = []

        # Find tag on download_files if they are known
        if release_download.get('files'):
            tag_files = release_download.get('files', [])

        # Find tag on all files in release folder
        else:
            for root, folders, names in os.walk(folder):
                tag_files.extend([sp(os.path.join(root, name)) for name in names if not os.path.splitext(name)[1] == '.ignore'])

        # Find all .ignore files in folder
        for root, dirnames, filenames in os.walk(folder):
            ignore_files.extend(fnmatch.filter([sp(os.path.join(root, filename)) for filename in filenames], '*%s.ignore' % tag))

        # Match all found ignore files with the tag_files and return True found
        for tag_file in tag_files:
            ignore_file = fnmatch.filter(ignore_files, fnEscape('%s.%s.ignore' % (os.path.splitext(tag_file)[0], tag if tag else '*')))
            if ignore_file:
                return True

        return False

    def moveFile(self, old, dest, forcemove = False):
        dest = sp(dest)
        try:
            if forcemove or self.conf('file_action') not in ['copy', 'link']:
                try:
                    shutil.move(old, dest)
                except:
                    if os.path.exists(dest):
                        log.error('Successfully moved file "%s", but something went wrong: %s', (dest, traceback.format_exc()))
                        os.unlink(old)
                    else:
                        raise
            elif self.conf('file_action') == 'copy':
                shutil.copy(old, dest)
            elif self.conf('file_action') == 'link':
                # First try to hardlink
                try:
                    log.debug('Hardlinking file "%s" to "%s"...', (old, dest))
                    link(old, dest)
                except:
                    # Try to simlink next
                    log.debug('Couldn\'t hardlink file "%s" to "%s". Simlinking instead. Error: %s.', (old, dest, traceback.format_exc()))
                    shutil.copy(old, dest)
                    try:
                        symlink(dest, old + '.link')
                        os.unlink(old)
                        os.rename(old + '.link', old)
                    except:
                        log.error('Couldn\'t symlink file "%s" to "%s". Copied instead. Error: %s. ', (old, dest, traceback.format_exc()))

            try:
                os.chmod(dest, Env.getPermission('file'))
                if os.name == 'nt' and self.conf('ntfs_permission'):
                    os.popen('icacls "' + dest + '"* /reset /T')
            except:
                log.error('Failed setting permissions for file: %s, %s', (dest, traceback.format_exc(1)))
        except:
            log.error('Couldn\'t move file "%s" to "%s": %s', (old, dest, traceback.format_exc()))
            raise

        return True

    def doReplace(self, string, replacements, remove_multiple = False, folder = False):
        """
        replace confignames with the real thing
        """

        replacements = replacements.copy()
        if remove_multiple:
            replacements['cd'] = ''
            replacements['cd_nr'] = ''

        replaced = toUnicode(string)
        for x, r in replacements.items():
            if x in ['thename', 'namethe']:
                continue
            if r is not None:
                replaced = replaced.replace(six.u('<%s>') % toUnicode(x), toUnicode(r))
            else:
                #If information is not available, we don't want the tag in the filename
                replaced = replaced.replace('<' + x + '>', '')

        replaced = self.replaceDoubles(replaced.lstrip('. '))
        for x, r in replacements.items():
            if x in ['thename', 'namethe']:
                replaced = replaced.replace(six.u('<%s>') % toUnicode(x), toUnicode(r))
        replaced = re.sub(r"[\x00:\*\?\"<>\|]", '', replaced)

        sep = self.conf('foldersep') if folder else self.conf('separator')
        return replaced.replace(' ', ' ' if not sep else sep)

    def replaceDoubles(self, string):

        replaces = [
            ('\.+', '.'), ('_+', '_'), ('-+', '-'), ('\s+', ' '), (' \\\\', '\\\\'), (' /', '/'),
            ('(\s\.)+', '.'), ('(-\.)+', '.'), ('(\s-)+', '-'),
        ]

        for r in replaces:
            reg, replace_with = r
            string = re.sub(reg, replace_with, string)

        return string

    def checkSnatched(self, fire_scan = True):

        if self.checking_snatched:
            log.debug('Already checking snatched')
            return False

        self.checking_snatched = True

        try:
            db = get_db()

            rels = list(fireEvent('release.with_status', ['snatched', 'seeding', 'missing'], single = True))

            if not rels:
                #No releases found that need status checking
                self.checking_snatched = False
                return True

            # Collect all download information with the download IDs from the releases
            download_ids = []
            no_status_support = []
            try:
                for rel in rels:
                    if not rel.get('download_info'): continue

                    if rel['download_info'].get('id') and rel['download_info'].get('downloader'):
                        download_ids.append(rel['download_info'])

                    ds = rel['download_info'].get('status_support')
                    if ds is False or ds == 'False':
                        no_status_support.append(ss(rel['download_info'].get('downloader')))
            except:
                log.error('Error getting download IDs from database')
                self.checking_snatched = False
                return False

            release_downloads = fireEvent('download.status', download_ids, merge = True) if download_ids else []

            if len(no_status_support) > 0:
                log.debug('Download status functionality is not implemented for one of the active downloaders: %s', list(set(no_status_support)))

            if not release_downloads:
                if fire_scan:
                    self.scan()

                self.checking_snatched = False
                return True

            scan_releases = []
            scan_required = False

            log.debug('Checking status snatched releases...')

            try:
                for rel in rels:
                    movie_dict = db.get('id', rel.get('media_id'))
                    download_info = rel.get('download_info')

                    if not isinstance(download_info, dict):
                        log.error('Faulty release found without any info, ignoring.')
                        fireEvent('release.update_status', rel.get('_id'), status = 'ignored', single = True)
                        continue

                    # Check if download ID is available
                    if not download_info.get('id') or not download_info.get('downloader'):
                        log.debug('Download status functionality is not implemented for downloader (%s) of release %s.', (download_info.get('downloader', 'unknown'), rel['info']['name']))
                        scan_required = True

                        # Continue with next release
                        continue

                    # Find release in downloaders
                    nzbname = self.createNzbName(rel['info'], movie_dict)

                    found_release = False
                    for release_download in release_downloads:
                        found_release = False
                        if download_info.get('id'):
                            if release_download['id'] == download_info['id'] and release_download['downloader'] == download_info['downloader']:
                                log.debug('Found release by id: %s', release_download['id'])
                                found_release = True
                                break
                        else:
                            if release_download['name'] == nzbname or rel['info']['name'] in release_download['name'] or getImdb(release_download['name']) == getIdentifier(movie_dict):
                                log.debug('Found release by release name or imdb ID: %s', release_download['name'])
                                found_release = True
                                break

                    if not found_release:
                        log.info('%s not found in downloaders', nzbname)

                        #Check status if already missing and for how long, if > 1 week, set to ignored else to missing
                        if rel.get('status') == 'missing':
                            if rel.get('last_edit') < int(time.time()) - 7 * 24 * 60 * 60:
                                fireEvent('release.update_status', rel.get('_id'), status = 'ignored', single = True)
                        else:
                            # Set the release to missing
                            fireEvent('release.update_status', rel.get('_id'), status = 'missing', single = True)

                        # Continue with next release
                        continue

                    # Log that we found the release
                    timeleft = 'N/A' if release_download['timeleft'] == -1 else release_download['timeleft']
                    log.debug('Found %s: %s, time to go: %s', (release_download['name'], release_download['status'].upper(), timeleft))

                    # Check status of release
                    if release_download['status'] == 'busy':
                        # Set the release to snatched if it was missing before
                        fireEvent('release.update_status', rel.get('_id'), status = 'snatched', single = True)

                        # Tag folder if it is in the 'from' folder and it will not be processed because it is still downloading
                        if self.movieInFromFolder(release_download['folder']):
                            self.tagRelease(release_download = release_download, tag = 'downloading')

                    elif release_download['status'] == 'seeding':
                        #If linking setting is enabled, process release
                        if self.conf('file_action') != 'move' and not rel.get('status') == 'seeding' and self.statusInfoComplete(release_download):
                            log.info('Download of %s completed! It is now being processed while leaving the original files alone for seeding. Current ratio: %s.', (release_download['name'], release_download['seed_ratio']))

                            # Remove the downloading tag
                            self.untagRelease(release_download = release_download, tag = 'downloading')

                            # Scan and set the torrent to paused if required
                            release_download.update({'pause': True, 'scan': True, 'process_complete': False})
                            scan_releases.append(release_download)
                        else:
                            #let it seed
                            log.debug('%s is seeding with ratio: %s', (release_download['name'], release_download['seed_ratio']))

                            # Set the release to seeding
                            fireEvent('release.update_status', rel.get('_id'), status = 'seeding', single = True)

                    elif release_download['status'] == 'failed':
                        # Set the release to failed
                        fireEvent('release.update_status', rel.get('_id'), status = 'failed', single = True)

                        fireEvent('download.remove_failed', release_download, single = True)

                        if self.conf('next_on_failed'):
                            fireEvent('movie.searcher.try_next_release', media_id = rel.get('media_id'))

                    elif release_download['status'] == 'completed':
                        log.info('Download of %s completed!', release_download['name'])

                        #Make sure the downloader sent over a path to look in
                        if self.statusInfoComplete(release_download):

                            # If the release has been seeding, process now the seeding is done
                            if rel.get('status') == 'seeding':
                                if self.conf('file_action') != 'move':
                                    # Set the release to done as the movie has already been renamed
                                    fireEvent('release.update_status', rel.get('_id'), status = 'downloaded', single = True)

                                    # Allow the downloader to clean-up
                                    release_download.update({'pause': False, 'scan': False, 'process_complete': True})
                                    scan_releases.append(release_download)
                                else:
                                    # Scan and Allow the downloader to clean-up
                                    release_download.update({'pause': False, 'scan': True, 'process_complete': True})
                                    scan_releases.append(release_download)

                            else:
                                # Set the release to snatched if it was missing before
                                fireEvent('release.update_status', rel.get('_id'), status = 'snatched', single = True)

                                # Remove the downloading tag
                                self.untagRelease(release_download = release_download, tag = 'downloading')

                                # Scan and Allow the downloader to clean-up
                                release_download.update({'pause': False, 'scan': True, 'process_complete': True})
                                scan_releases.append(release_download)
                        else:
                            scan_required = True

            except:
                log.error('Failed checking for release in downloader: %s', traceback.format_exc())

            # The following can either be done here, or inside the scanner if we pass it scan_items in one go
            for release_download in scan_releases:
                # Ask the renamer to scan the item
                if release_download['scan']:
                    if release_download['pause'] and self.conf('file_action') == 'link':
                        fireEvent('download.pause', release_download = release_download, pause = True, single = True)
                    self.scan(release_download = release_download)
                    if release_download['pause'] and self.conf('file_action') == 'link':
                        fireEvent('download.pause', release_download = release_download, pause = False, single = True)
                if release_download['process_complete']:
                    # First make sure the files were successfully processed
                    if not self.hastagRelease(release_download = release_download, tag = 'failed_rename'):
                        # Remove the seeding tag if it exists
                        self.untagRelease(release_download = release_download, tag = 'renamed_already')
                        # Ask the downloader to process the item
                        fireEvent('download.process_complete', release_download = release_download, single = True)

            if fire_scan and (scan_required or len(no_status_support) > 0):
                self.scan()

            self.checking_snatched = False
            return True
        except:
            log.error('Failed checking snatched: %s', traceback.format_exc())

        self.checking_snatched = False
        return False

    def extendReleaseDownload(self, release_download):

        rls = None
        db = get_db()

        if release_download and release_download.get('id'):
            try:
                rls = db.get('release_download', '%s-%s' % (release_download.get('downloader'), release_download.get('id')), with_doc = True)['doc']
            except:
                log.error('Download ID %s from downloader %s not found in releases', (release_download.get('id'), release_download.get('downloader')))

        if rls:
            media = db.get('id', rls['media_id'])
            release_download.update({
                'imdb_id': getIdentifier(media),
                'quality': rls['quality'],
                'is_3d': rls['is_3d'],
                'protocol': rls.get('info', {}).get('protocol') or rls.get('info', {}).get('type'),
                'release_id': rls['_id'],
            })

        return release_download

    def downloadIsTorrent(self, release_download):
        return release_download and release_download.get('protocol') in ['torrent', 'torrent_magnet']

    def fileIsAdded(self, src, group):
        if not group or not group.get('before_rename'):
            return False
        return src in group['before_rename']

    def statusInfoComplete(self, release_download):
        return release_download.get('id') and release_download.get('downloader') and release_download.get('folder')

    def movieInFromFolder(self, media_folder):
        return media_folder and isSubFolder(media_folder, sp(self.conf('from'))) or not media_folder

    def extractFiles(self, folder = None, media_folder = None, files = None, cleanup = False):
        if not files: files = []

        # RegEx for finding rar files
        archive_regex = '(?P<file>^(?P<base>(?:(?!\.part\d+\.rar$).)*)\.(?:(?:part0*1\.)?rar)$)'
        restfile_regex = '(^%s\.(?:part(?!0*1\.rar$)\d+\.rar$|[rstuvw]\d+$))'
        extr_files = []

        from_folder = sp(self.conf('from'))

        # Check input variables
        if not folder:
            folder = from_folder

        check_file_date = True
        if media_folder:
            check_file_date = False

        if not files:
            for root, folders, names in os.walk(folder):
                files.extend([sp(os.path.join(root, name)) for name in names])

        # Find all archive files
        archives = [re.search(archive_regex, name).groupdict() for name in files if re.search(archive_regex, name)]

        #Extract all found archives
        for archive in archives:
            # Check if it has already been processed by CPS
            if self.hastagRelease(release_download = {'folder': os.path.dirname(archive['file']), 'files': archive['file']}):
                continue

            # Find all related archive files
            archive['files'] = [name for name in files if re.search(restfile_regex % re.escape(archive['base']), name)]
            archive['files'].append(archive['file'])

            # Check if archive is fresh and maybe still copying/moving/downloading, ignore files newer than 1 minute
            if check_file_date:
                files_too_new, time_string = self.checkFilesChanged(archive['files'])

                if files_too_new:
                    log.info('Archive seems to be still copying/moving/downloading or just copied/moved/downloaded (created on %s), ignoring for now: %s', (time_string, os.path.basename(archive['file'])))
                    continue

            log.info('Archive %s found. Extracting...', os.path.basename(archive['file']))
            try:
                rar_handle = RarFile(archive['file'])
                extr_path = os.path.join(from_folder, os.path.relpath(os.path.dirname(archive['file']), folder))
                self.makeDir(extr_path)
                for packedinfo in rar_handle.infolist():
                    if not packedinfo.isdir and not os.path.isfile(sp(os.path.join(extr_path, os.path.basename(packedinfo.filename)))):
                        log.debug('Extracting %s...', packedinfo.filename)
                        rar_handle.extract(condition = [packedinfo.index], path = extr_path, withSubpath = False, overwrite = False)
                        extr_files.append(sp(os.path.join(extr_path, os.path.basename(packedinfo.filename))))
                del rar_handle
            except Exception as e:
                log.error('Failed to extract %s: %s %s', (archive['file'], e, traceback.format_exc()))
                continue

            # Delete the archive files
            for filename in archive['files']:
                if cleanup:
                    try:
                        os.remove(filename)
                    except Exception as e:
                        log.error('Failed to remove %s: %s %s', (filename, e, traceback.format_exc()))
                        continue
                files.remove(filename)

        # Move the rest of the files and folders if any files are extracted to the from folder (only if folder was provided)
        if extr_files and folder != from_folder:
            for leftoverfile in list(files):
                move_to = os.path.join(from_folder, os.path.relpath(leftoverfile, folder))

                try:
                    self.makeDir(os.path.dirname(move_to))
                    self.moveFile(leftoverfile, move_to, cleanup)
                except Exception as e:
                    log.error('Failed moving left over file %s to %s: %s %s', (leftoverfile, move_to, e, traceback.format_exc()))
                    # As we probably tried to overwrite the nfo file, check if it exists and then remove the original
                    if os.path.isfile(move_to):
                        if cleanup:
                            log.info('Deleting left over file %s instead...', leftoverfile)
                            os.unlink(leftoverfile)
                    else:
                        continue

                files.remove(leftoverfile)
                extr_files.append(move_to)

            if cleanup:
                # Remove all left over folders
                log.debug('Removing old movie folder %s...', media_folder)
                self.deleteEmptyFolder(media_folder)

            media_folder = os.path.join(from_folder, os.path.relpath(media_folder, folder))
            folder = from_folder

        if extr_files:
            files.extend(extr_files)

        # Cleanup files and folder if media_folder was not provided
        if not media_folder:
            files = []
            folder = None

        return folder, media_folder, files, extr_files


rename_options = {
    'pre': '<',
    'post': '>',
    'choices': {
        'ext': 'Extention (mkv)',
        'namethe': 'Moviename, The',
        'thename': 'The Moviename',
        'year': 'Year (2011)',
        'first': 'First letter (M)',
        'quality': 'Quality (720p)',
        'quality_type': '(HD) or (SD)',
        '3d': '3D',
        '3d_type': '3D Type (Full SBS)',
        'video': 'Video (x264)',
        'audio': 'Audio (DTS)',
        'group': 'Releasegroup name',
        'source': 'Source media (Bluray)',
        'resolution_width': 'resolution width (1280)',
        'resolution_height': 'resolution height (720)',
        'audio_channels': 'audio channels (7.1)',
        'original': 'Original filename',
        'original_folder': 'Original foldername',
        'imdb_id': 'IMDB id (tt0123456)',
        'cd': 'CD number (cd1)',
        'cd_nr': 'Just the cd nr. (1)',
        'mpaa': 'MPAA or other certification',
        'mpaa_only': 'MPAA only certification (G|PG|PG-13|R|NC-17|Not Rated)',
        'category': 'Category label',
    },
}

config = [{
    'name': 'renamer',
    'order': 40,
    'description': 'Move and rename your downloaded movies to your movie directory.',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'renamer',
            'label': 'Rename downloaded movies',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'from',
                    'type': 'directory',
                    'description': 'Folder where CP searches for movies.',
                },
                {
                    'name': 'to',
                    'type': 'directory',
                    'description': 'Default folder where the movies are moved to.',
                },
                {
                    'name': 'folder_name',
                    'label': 'Folder naming',
                    'description': 'Name of the folder. Keep empty for no folder.',
                    'default': '<namethe> (<year>)',
                    'type': 'choice',
                    'options': rename_options
                },
                {
                    'name': 'file_name',
                    'label': 'File naming',
                    'description': 'Name of the file',
                    'default': '<thename><cd>.<ext>',
                    'type': 'choice',
                    'options': rename_options
                },
                {
                    'name': 'unrar',
                    'type': 'bool',
                    'description': 'Extract rar files if found.',
                    'default': False,
                },
                {
                    'name': 'cleanup',
                    'type': 'bool',
                    'description': 'Cleanup leftover files after successful rename.',
                    'default': False,
                },
                {
                    'advanced': True,
                    'name': 'run_every',
                    'label': 'Run every',
                    'default': 1,
                    'type': 'int',
                    'unit': 'min(s)',
                    'description': ('Detect movie status every X minutes.', 'Will start the renamer if movie is <strong>completed</strong> or handle <strong>failed</strong> download if these options are enabled'),
                },
                {
                    'advanced': True,
                    'name': 'force_every',
                    'label': 'Force every',
                    'default': 2,
                    'type': 'int',
                    'unit': 'hour(s)',
                    'description': 'Forces the renamer to scan every X hours',
                },
                {
                    'advanced': True,
                    'name': 'next_on_failed',
                    'default': True,
                    'type': 'bool',
                    'description': 'Try the next best release for a movie after a download failed.',
                },
                {
                    'name': 'move_leftover',
                    'type': 'bool',
                    'description': 'Move all leftover file after renaming, to the movie folder.',
                    'default': False,
                    'advanced': True,
                },
                {
                    'advanced': True,
                    'name': 'separator',
                    'label': 'File-Separator',
                    'description': ('Replace all the spaces with a character.', 'Example: ".", "-" (without quotes). Leave empty to use spaces.'),
                },
                {
                    'advanced': True,
                    'name': 'foldersep',
                    'label': 'Folder-Separator',
                    'description': ('Replace all the spaces with a character.', 'Example: ".", "-" (without quotes). Leave empty to use spaces.'),
                },
                {
                    'name': 'file_action',
                    'label': 'Torrent File Action',
                    'default': 'link',
                    'type': 'dropdown',
                    'values': [('Link', 'link'), ('Copy', 'copy'), ('Move', 'move')],
                    'description': ('<strong>Link</strong>, <strong>Copy</strong> or <strong>Move</strong> after download completed.',
                                    'Link first tries <a href="http://en.wikipedia.org/wiki/Hard_link">hard link</a>, then <a href="http://en.wikipedia.org/wiki/Sym_link">sym link</a> and falls back to Copy. It is perfered to use link when downloading torrents as it will save you space, while still beeing able to seed.'),
                    'advanced': True,
                },
                {
                    'advanced': True,
                    'name': 'ntfs_permission',
                    'label': 'NTFS Permission',
                    'type': 'bool',
                    'hidden': os.name != 'nt',
                    'description': 'Set permission of moved files to that of destination folder (Windows NTFS only).',
                    'default': False,
                },
            ],
        }, {
            'tab': 'renamer',
            'name': 'meta_renamer',
            'label': 'Advanced renaming',
            'description': 'Meta data file renaming. Use &lt;filename&gt; to use the above "File naming" settings, without the file extention.',
            'advanced': True,
            'options': [
                {
                    'name': 'rename_nfo',
                    'label': 'Rename .NFO',
                    'description': 'Rename original .nfo file',
                    'type': 'bool',
                    'default': True,
                },
                {
                    'name': 'nfo_name',
                    'label': 'NFO naming',
                    'default': '<filename>.orig.<ext>',
                    'type': 'choice',
                    'options': rename_options
                },
            ],
        },
    ],
}]
