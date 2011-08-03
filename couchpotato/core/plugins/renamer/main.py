from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
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

    def __init__(self):

        addEvent('renamer.scan', self.scan)
        addEvent('app.load', self.scan)

        fireEvent('schedule.interval', 'renamer.scan', self.scan, minutes = self.conf('run_every'))

    def scan(self):

        groups = fireEvent('scanner.scan', folder = self.conf('from'), single = True)
        if groups is None: return

        destination = self.conf('to')
        folder_name = self.conf('folder_name')
        file_name = self.conf('file_name')
        trailer_name = self.conf('trailer_name')
        backdrop_name = self.conf('fanart_name')
        nfo_name = self.conf('nfo_name')
        separator = self.conf('separator')

        for group_identifier in groups:

            group = groups[group_identifier]
            rename_files = {}

            # Add _UNKNOWN_ if no library is connected
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

                    # Move DVD files (no renaming)
                    if group['is_dvd'] and file_type is 'movie':
                        continue

                    # Move nfo depending on settings
                    if file_type is 'nfo' and not self.conf('rename_nfo'):
                        continue

                    # Subtitle extra
                    if file_type is 'subtitle_extra':
                        continue

                    # Move other files
                    multiple = len(group['files']['movie']) > 1
                    cd = 1 if multiple else 0

                    for file in sorted(list(group['files'][file_type])):

                        # Original filename
                        replacements['original'] = os.path.basename(file)

                        # Extension
                        replacements['ext'] = getExt(file)

                        # cd #
                        replacements['cd'] = ' cd%d' % cd if cd else ''
                        replacements['cd_nr'] = cd

                        # Naming
                        final_folder_name = self.doReplace(folder_name, replacements)
                        final_file_name = self.doReplace(file_name, replacements)
                        replacements['filename'] = final_file_name[:-(len(getExt(final_file_name)) + 1)]

                        # Meta naming
                        if file_type is 'trailer':
                            final_file_name = self.doReplace(trailer_name, replacements)
                        elif file_type is 'nfo':
                            final_file_name = self.doReplace(nfo_name, replacements)
                        elif file_type is 'backdrop':
                            final_file_name = self.doReplace(backdrop_name, replacements)

                        # Seperator replace
                        if separator:
                            final_file_name = final_file_name.replace(' ', separator)

                        # Main file
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

                        if multiple:
                            cd += 1

                # Before renaming, remove the lower quality files
                db = get_session()
                library = db.query(Library).filter_by(identifier = group['library']['identifier']).first()
                done_status = fireEvent('status.get', 'done', single = True)
                for movie in library.movies:
                    for release in movie.releases:
                        if release.quality.order < group['meta_data']['quality']['order']:
                            log.info('Removing older release for %s, with quality %s' % (movie.library.titles[0].title, release.quality.label))
                        elif release.status_id is done_status.get('id'):
                            if release.quality.order is group['meta_data']['quality']['order']:
                                log.info('Same quality release already exists for %s, with quality %s. Assuming repack.' % (movie.library.titles[0].title, release.quality.label))
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

                                break

                        for file in release.files:
                            log.info('Removing (not really) "%s"' % file.path)

            # Rename
            for src in rename_files:
                if rename_files[src]:

                    dst = rename_files[src]

                    log.info('Renaming "%s" to "%s"' % (src, dst))

                    path = os.path.dirname(dst)
                    try:
                        if not os.path.isdir(path): os.makedirs(path)
                    except:
                        log.error('Failed creating dir %s: %s' % (path, traceback.format_exc()))
                        continue

                    try:
                        shutil.move(src, dst)
                    except:
                        log.error('Failed moving the file "%s" : %s' % (os.path.basename(src), traceback.format_exc()))

                #print rename_me, rename_files[rename_me]

            # Search for trailers
            fireEvent('renamer.after', group)

    def moveFile(self, old, dest, suppress = True):
        try:
            shutil.move(old, dest)
        except:
            log.error("Couldn't move file '%s' to '%s': %s" % (old, dest, traceback.format_exc()))
            return False

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
