from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library
import os.path
import re
import shutil
import traceback

log = CPLog(__name__)


class Renamer(Plugin):

    renaming_started = False

    def __init__(self):

        addEvent('renamer.scan', self.scan)
        addEvent('app.load', self.scan)

        fireEvent('schedule.interval', 'renamer.scan', self.scan, minutes = self.conf('run_every'))

    def scan(self):

        if self.isDisabled():
            return

        if self.renaming_started is True:
            log.error('Renamer is disabled to avoid infinite looping of the same error.')
            return

        # Check to see if the "to" folder is inside the "from" folder.
        if self.conf('from') in self.conf('to'):
            log.error('The "to" can\'t be inside of the "from" folder. You\'ll get an infinite loop.')
            return

        groups = fireEvent('scanner.scan', folder = self.conf('from'), single = True)
        if groups is None: return

        self.renaming_started = True

        destination = self.conf('to')
        folder_name = self.conf('folder_name')
        file_name = self.conf('file_name')
        trailer_name = self.conf('trailer_name')
        nfo_name = self.conf('nfo_name')
        separator = self.conf('separator')

        for group_identifier in groups:

            group = groups[group_identifier]
            rename_files = {}
            remove_files = []
            remove_releases = []

            # Add _UNKNOWN_ if no library item is connected
            if not group['library']:
                if group['dirname']:
                    rename_files[group['parentdir']] = group['parentdir'].replace(group['dirname'], '_UNKNOWN_%s' % group['dirname'])
                else: # Add it to filename
                    for file_type in group['files']:
                        for rename_me in group['files'][file_type]:
                            filename = os.path.basename(rename_me)
                            rename_files[rename_me] = rename_me.replace(filename, '_UNKNOWN_%s' % filename)

            # Rename the files using the library data
            else:
                group['library'] = fireEvent('library.update', identifier = group['library']['identifier'], single = True)
                if not group['library']:
                    log.error('Could not rename, no library item to work with: %s' % group_identifier)
                    continue

                library = group['library']

                # Find subtitle for renaming
                fireEvent('renamer.before', group)

                # Remove weird chars from moviename
                movie_name = re.sub(r"[\x00\/\\:\*\?\"<>\|]", '', group['library']['titles'][0]['title'])

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
                     'dirname': group['dirname'],
                     'quality': group['meta_data']['quality']['label'],
                     'quality_type': group['meta_data']['quality_type'],
                     'video': group['meta_data'].get('video'),
                     'audio': group['meta_data'].get('audio'),
                     'group': group['meta_data']['group'],
                     'source': group['meta_data']['source'],
                     'resolution_width': group['meta_data'].get('resolution_width'),
                     'resolution_height': group['meta_data'].get('resolution_height'),
                }

                for file_type in group['files']:

                    # Move nfo depending on settings
                    if file_type is 'nfo' and not self.conf('rename_nfo'):
                        log.debug('Skipping, renaming of %s disabled' % file_type)
                        continue

                    # Subtitle extra
                    if file_type is 'subtitle_extra':
                        continue

                    # Move other files
                    multiple = len(group['files']['movie']) > 1 and not group['is_dvd']
                    cd = 1 if multiple else 0

                    for file in sorted(list(group['files'][file_type])):

                        # Original filename
                        replacements['original'] = os.path.basename(file)
                        replacements['original_folder'] = os.path.basename(os.path.dirname(file))

                        # Extension
                        replacements['ext'] = getExt(file)

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
                        group['filename'] = self.doReplace(file_name, replacements)[:-(len(getExt(final_file_name)) + 1)]

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
                                has_string = file.lower().find(os.path.sep + top_dir + os.path.sep)
                                if has_string >= 0:
                                    structure_dir = file[has_string:].lstrip(os.path.sep)
                                    rename_files[file] = os.path.join(destination, final_folder_name, structure_dir)
                                    found = True
                                    break

                            if not found:
                                log.error('Could not determin dvd structure for: %s' % file)

                        # Do rename others
                        else:
                            if self.conf('move_leftover') and file_type is 'leftover':
                                rename_files[file] = os.path.join(destination, final_folder_name, os.path.basename(file))
                            else:
                                rename_files[file] = os.path.join(destination, final_folder_name, final_file_name)

                        # Check for extra subtitle files
                        if file_type is 'subtitle':

                            def test(s):
                                return file[:-len(replacements['ext'])] in s

                            for subtitle_extra in set(filter(test, group['files']['subtitle_extra'])):
                                replacements['ext'] = getExt(subtitle_extra)

                                final_folder_name = self.doReplace(folder_name, replacements)
                                final_file_name = self.doReplace(file_name, replacements)
                                rename_files[subtitle_extra] = os.path.join(destination, final_folder_name, final_file_name)

                        # Filename without cd etc
                        if file_type is 'movie':
                            group['destination_dir'] = os.path.join(destination, final_folder_name)

                        if multiple:
                            cd += 1

                # Before renaming, remove the lower quality files
                db = get_session()

                library = db.query(Library).filter_by(identifier = group['library']['identifier']).first()
                done_status = fireEvent('status.get', 'done', single = True)
                active_status = fireEvent('status.get', 'active', single = True)

                for movie in library.movies:

                    # Mark movie "done" onces it found the quality with the finish check
                    try:
                        if movie.status_id == active_status.get('id'):
                            for type in movie.profile.types:
                                if type.quality_id == group['meta_data']['quality']['id'] and type.finish:
                                    movie.status_id = done_status.get('id')
                                    db.commit()
                    except Exception, e:
                        log.error('Failed marking movie finished: %s %s' % (e, traceback.format_exc()))

                    # Go over current movie releases
                    for release in movie.releases:

                        # When a release already exists
                        if release.status_id is done_status.get('id'):

                            # This is where CP removes older, lesser quality releases
                            if release.quality.order > group['meta_data']['quality']['order']:
                                log.info('Removing lesser quality %s for %s.' % (movie.library.titles[0].title, release.quality.label))
                                for file in release.files:
                                    remove_files.append(file)
                                remove_releases.append(release)
                            # Same quality, but still downloaded, so maybe repack/proper/unrated/directors cut etc
                            elif release.quality.order is group['meta_data']['quality']['order']:
                                log.info('Same quality release already exists for %s, with quality %s. Assuming repack.' % (movie.library.titles[0].title, release.quality.label))
                                for file in release.files:
                                    remove_files.append(file)
                                remove_releases.append(release)

                            # Downloaded a lower quality, rename the newly downloaded files/folder to exclude them from scan
                            else:
                                log.info('Better quality release already exists for %s, with quality %s' % (movie.library.titles[0].title, release.quality.label))

                                # Add _EXISTS_ to the parent dir
                                if group['dirname']:
                                    for rename_me in rename_files: # Don't rename anything in this group
                                        rename_files[rename_me] = None
                                    rename_files[group['parentdir']] = group['parentdir'].replace(group['dirname'], '_EXISTS_%s' % group['dirname'])
                                else: # Add it to filename
                                    for rename_me in rename_files:
                                        filename = os.path.basename(rename_me)
                                        rename_files[rename_me] = rename_me.replace(filename, '_EXISTS_%s' % filename)

                                # Notify on rename fail
                                download_message = 'Renaming of %s (%s) canceled, exists in %s already.' % (movie.library.titles[0].title, group['meta_data']['quality']['label'], release.quality.label)
                                fireEvent('movie.renaming.canceled', message = download_message, data = group)

                                break

                # Remove leftover files
                if self.conf('cleanup') and not self.conf('move_leftover'):
                    log.debug('Removing leftover files')
                    for file in group['files']['leftover']:
                        remove_files.append(file)

            # Rename all files marked
            for src in rename_files:
                if rename_files[src]:
                    dst = rename_files[src]
                    log.info('Renaming "%s" to "%s"' % (src, dst))

                    # Create dir
                    self.makeDir(os.path.dirname(dst))

                    try:
                        self.moveFile(src, dst)
                    except:
                        log.error('Failed moving the file "%s" : %s' % (os.path.basename(src), traceback.format_exc()))

            # Remove files
            for src in remove_files:
                log.info('Removing "%s"' % src)

            # Remove matching releases
            for release in remove_releases:
                log.info('Removing release %s' % release)

            # Add this release to the library
            fireEvent('scanner.files', folder = destination, files = rename_files)

            # Search for trailers etc
            fireEventAsync('renamer.after', group)

            # Notify on download
            download_message = 'Downloaded %s (%s) successfully.' % (group['library']['titles'][0]['title'], replacements['quality'])
            fireEventAsync('movie.downloaded', message = download_message, data = group)

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        self.renaming_started = False

    def moveFile(self, old, dest):
        try:
            shutil.move(old, dest)
        except:
            log.error("Couldn't move file '%s' to '%s': %s" % (old, dest, traceback.format_exc()))
            raise Exception

        return True

    def doReplace(self, string, replacements):
        '''
        replace confignames with the real thing
        '''

        replaced = toUnicode(string)
        for x, r in replacements.iteritems():
            if r is not None:
                replaced = replaced.replace('<%s>' % toUnicode(x), toUnicode(r))
            else:
                #If information is not available, we don't want the tag in the filename
                replaced = replaced.replace('<' + x + '>', '')

        replaced = re.sub(r"[\x00:\*\?\"<>\|]", '', replaced)

        sep = self.conf('separator')
        return self.replaceDoubles(replaced).replace(' ', ' ' if not sep else sep)

    def replaceDoubles(self, string):
        return string.replace('  ', ' ').replace(' .', '.')
