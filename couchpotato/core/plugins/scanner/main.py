from couchpotato import get_session
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.helpers.variable import getExt, getImdb, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import File
from couchpotato.environment import Env
from enzyme.exceptions import NoParserError, ParseError
from guessit import guess_movie_info
from subliminal.videos import scan
import enzyme
import logging
import os
import re
import time
import traceback

enzyme_logger = logging.getLogger('enzyme')
enzyme_logger.setLevel(logging.INFO)

log = CPLog(__name__)


class Scanner(Plugin):

    minimal_filesize = {
        'media': 314572800, # 300MB
        'trailer': 1048576, # 1MB
    }
    ignored_in_path = ['_unpack', '_failed_', '_unknown_', '_exists_', '.appledouble', '.appledb', '.appledesktop', os.path.sep + '._', '.ds_store', 'cp.cpnfo'] #unpacking, smb-crap, hidden files
    ignore_names = ['extract', 'extracting', 'extracted', 'movie', 'movies', 'film', 'films', 'download', 'downloads', 'video_ts', 'audio_ts', 'bdmv', 'certificate']
    extensions = {
        'movie': ['mkv', 'wmv', 'avi', 'mpg', 'mpeg', 'mp4', 'm2ts', 'iso', 'img', 'mdf'],
        'movie_extra': ['mds'],
        'dvd': ['vts_*', 'vob'],
        'nfo': ['nfo', 'txt', 'tag'],
        'subtitle': ['sub', 'srt', 'ssa', 'ass'],
        'subtitle_extra': ['idx'],
        'trailer': ['mov', 'mp4', 'flv']
    }
    file_types = {
        'subtitle': ('subtitle', 'subtitle'),
        'subtitle_extra': ('subtitle', 'subtitle_extra'),
        'trailer': ('video', 'trailer'),
        'nfo': ('nfo', 'nfo'),
        'movie': ('video', 'movie'),
        'movie_extra': ('movie', 'movie_extra'),
        'backdrop': ('image', 'backdrop'),
        'leftover': ('leftover', 'leftover'),
    }

    codecs = {
        'audio': ['dts', 'ac3', 'ac3d', 'mp3'],
        'video': ['x264', 'h264', 'divx', 'xvid']
    }

    source_media = {
        'bluray': ['bluray', 'blu-ray', 'brrip', 'br-rip'],
        'hddvd': ['hddvd', 'hd-dvd'],
        'dvd': ['dvd'],
        'hdtv': ['hdtv']
    }

    clean = '[ _\,\.\(\)\[\]\-](french|swedisch|danish|dutch|swesub|spanish|german|ac3|dts|custom|dc|divx|divx5|dsr|dsrip|dutch|dvd|dvdr|dvdrip|dvdscr|dvdscreener|screener|dvdivx|cam|fragment|fs|hdtv|hdrip|hdtvrip|internal|limited|multisubs|ntsc|ogg|ogm|pal|pdtv|proper|repack|rerip|retail|r3|r5|bd5|se|svcd|swedish|german|read.nfo|nfofix|unrated|ws|telesync|ts|telecine|tc|brrip|bdrip|video_ts|audio_ts|480p|480i|576p|576i|720p|720i|1080p|1080i|hrhd|hrhdtv|hddvd|bluray|x264|h264|xvid|xvidvd|xxx|www.www|cd[1-9]|\[.*\])([ _\,\.\(\)\[\]\-]|$)'
    multipart_regex = [
        '[ _\.-]+cd[ _\.-]*([0-9a-d]+)', #*cd1
        '[ _\.-]+dvd[ _\.-]*([0-9a-d]+)', #*dvd1
        '[ _\.-]+part[ _\.-]*([0-9a-d]+)', #*part1
        '[ _\.-]+dis[ck][ _\.-]*([0-9a-d]+)', #*disk1
        'cd[ _\.-]*([0-9a-d]+)$', #cd1.ext
        'dvd[ _\.-]*([0-9a-d]+)$', #dvd1.ext
        'part[ _\.-]*([0-9a-d]+)$', #part1.mkv
        'dis[ck][ _\.-]*([0-9a-d]+)$', #disk1.mkv
        '()[ _\.-]+([0-9]*[abcd]+)(\.....?)$',
        '([a-z])([0-9]+)(\.....?)$',
        '()([ab])(\.....?)$' #*a.mkv
    ]

    cp_imdb = '(\.cp\((?P<id>tt[0-9{7}]+)\))'

    path_identifiers = {} # bind identifier to filepath

    def __init__(self):

        addEvent('scanner.create_file_identifier', self.createStringIdentifier)
        addEvent('scanner.remove_cptag', self.removeCPTag)

        addEvent('scanner.scan', self.scan)
        addEvent('scanner.files', self.scanFilesToLibrary)
        addEvent('scanner.folder', self.scanFolderToLibrary)
        addEvent('scanner.name_year', self.getReleaseNameYear)
        addEvent('scanner.partnumber', self.getPartNumber)

        def after_rename(group):
            return self.scanFilesToLibrary(self, folder = group['destination_dir'], files = group['renamed_files'])

        addEvent('rename.after', after_rename)

        # Disable lib logging
        logging.getLogger('guessit').setLevel(logging.ERROR)
        logging.getLogger('subliminal').setLevel(logging.ERROR)

    def scanFilesToLibrary(self, folder = None, files = None):

        groups = self.scan(folder = folder, files = files)

        for group in groups.itervalues():
            if group['library']:
                fireEvent('release.add', group = group)

    def scanFolderToLibrary(self, folder = None, newer_than = None):

        if not os.path.isdir(folder):
            return

        groups = self.scan(folder = folder)

        added_identifier = []
        while True and not self.shuttingDown():
            try:
                identifier, group = groups.popitem()
            except:
                break

            # Save to DB
            if group['library']:

                # Add release
                fireEvent('release.add', group = group)
                library_item = fireEvent('library.update', identifier = group['library'].get('identifier'), single = True)
                added_identifier.append(library_item['identifier'])

        return added_identifier


    def scan(self, folder = None, files = []):

        if not folder or not os.path.isdir(folder):
            log.error('Folder doesn\'t exists: %s' % folder)
            return {}

        # Get movie "master" files
        movie_files = {}
        leftovers = []

        # Scan all files of the folder if no files are set
        if len(files) == 0:
            try:
                files = []
                for root, dirs, walk_files in os.walk(toUnicode(folder)):
                    for filename in walk_files:
                        files.append(os.path.join(root, filename))
            except:
                try:
                    files = []
                    folder = toUnicode(folder).encode(Env.get('encoding'))
                    log.info('Trying to convert unicode to str path: %s, %s' % (folder, type(folder)))
                    for root, dirs, walk_files in os.walk(folder):
                        for filename in walk_files:
                            files.append(os.path.join(root, filename))
                except:
                    log.error('Failed getting files from %s: %s' % (folder, traceback.format_exc()))

        for file_path in files:

            # Remove ignored files
            if self.isSampleFile(file_path):
                leftovers.append(file_path)
                continue
            elif not self.keepFile(file_path):
                continue

            is_dvd_file = self.isDVDFile(file_path)
            if os.path.getsize(file_path) > self.minimal_filesize['media'] or is_dvd_file: # Minimal 300MB files or is DVD file

                # Normal identifier
                identifier = self.createStringIdentifier(file_path, folder, exclude_filename = is_dvd_file)

                # Identifier with quality
                quality = fireEvent('quality.guess', [file_path], single = True) if not is_dvd_file else {'identifier':'dvdr'}
                identifier_with_quality = '%s %s' % (identifier, quality.get('identifier', ''))

                if not movie_files.get(identifier):
                    movie_files[identifier] = {
                        'unsorted_files': [],
                        'identifiers': [identifier_with_quality, identifier],
                        'is_dvd': is_dvd_file,
                    }

                movie_files[identifier]['unsorted_files'].append(file_path)
            else:
                leftovers.append(file_path)

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        # Cleanup
        del files

        # Sort reverse, this prevents "Iron man 2" from getting grouped with "Iron man" as the "Iron Man 2"
        # files will be grouped first.
        leftovers = set(sorted(leftovers, reverse = True))


        # Group files minus extension
        for identifier, group in movie_files.iteritems():
            if identifier not in group['identifiers'] and len(identifier) > 0: group['identifiers'].append(identifier)

            log.debug('Grouping files: %s' % identifier)

            for file_path in group['unsorted_files']:
                wo_ext = file_path[:-(len(getExt(file_path)) + 1)]
                found_files = set([i for i in leftovers if wo_ext in i])
                group['unsorted_files'].extend(found_files)
                leftovers = leftovers - found_files

            # Break if CP wants to shut down
            if self.shuttingDown():
                break


        # Create identifiers for all leftover files
        for file_path in leftovers:
            identifier = self.createStringIdentifier(file_path, folder)

            if not self.path_identifiers.get(identifier):
                self.path_identifiers[identifier] = []

            self.path_identifiers[identifier].append(file_path)


        # Group the files based on the identifier
        for identifier, group in movie_files.iteritems():
            log.debug('Grouping files on identifier: %s' % identifier)

            found_files = set(self.path_identifiers.get(identifier, []))
            group['unsorted_files'].extend(found_files)

            # Remove the found files from the leftover stack
            leftovers = leftovers - found_files

            # Break if CP wants to shut down
            if self.shuttingDown():
                break


        # Determine file types
        processed_movies = {}
        while True and not self.shuttingDown():
            try:
                identifier, group = movie_files.popitem()
            except:
                break

            # Check if movie is fresh and maybe still unpacking, ignore files new then 1 minute
            file_too_new = False
            for cur_file in group['unsorted_files']:
                file_time = os.path.getmtime(cur_file)
                if file_time > time.time() - 60:
                    file_too_new = tryInt(time.time() - file_time)
                    break

            if file_too_new and not Env.get('dev'):
                log.info('Files seem to be still unpacking or just unpacked (created on %s), ignoring for now: %s' % (time.ctime(file_time), identifier))
                continue

            # Group extra (and easy) files first
            # images = self.getImages(group['unsorted_files'])
            group['files'] = {
                'movie_extra': self.getMovieExtras(group['unsorted_files']),
                'subtitle': self.getSubtitles(group['unsorted_files']),
                'subtitle_extra': self.getSubtitlesExtras(group['unsorted_files']),
                'nfo': self.getNfo(group['unsorted_files']),
                'trailer': self.getTrailers(group['unsorted_files']),
                #'backdrop': images['backdrop'],
                'leftover': set(group['unsorted_files']),
            }

            # Media files
            if group['is_dvd']:
                group['files']['movie'] = self.getDVDFiles(group['unsorted_files'])
            else:
                group['files']['movie'] = self.getMediaFiles(group['unsorted_files'])

            if len(group['files']['movie']) == 0:
                log.error('Couldn\t find any movie files for %s' % identifier)
                continue

            log.debug('Getting metadata for %s' % identifier)
            group['meta_data'] = self.getMetaData(group)

            # Subtitle meta
            group['subtitle_language'] = self.getSubtitleLanguage(group)

            # Get parent dir from movie files
            for movie_file in group['files']['movie']:
                group['parentdir'] = os.path.dirname(movie_file)
                group['dirname'] = None

                folder_names = group['parentdir'].replace(folder, '').split(os.path.sep)
                folder_names.reverse()

                # Try and get a proper dirname, so no "A", "Movie", "Download" etc
                for folder_name in folder_names:
                    if folder_name.lower() not in self.ignore_names and len(folder_name) > 2:
                        group['dirname'] = folder_name
                        break

                break

            # Leftover "sorted" files
            for file_type in group['files']:
                if not file_type is 'leftover':
                    group['files']['leftover'] -= set(group['files'][file_type])

            # Delete the unsorted list
            del group['unsorted_files']

            # Determine movie
            group['library'] = self.determineMovie(group)
            if not group['library']:
                log.error('Unable to determin movie: %s' % group['identifiers'])

            processed_movies[identifier] = group


        # Clean up
        self.path_identifiers = {}

        return processed_movies

    def getMetaData(self, group):

        data = {}
        files = list(group['files']['movie'])

        for cur_file in files:
            if os.path.getsize(cur_file) < self.minimal_filesize['media']: continue # Ignore smaller files

            meta = self.getMeta(cur_file)

            try:
                data['video'] = meta.get('video', self.getCodec(cur_file, self.codecs['video']))
                data['audio'] = meta.get('audio', self.getCodec(cur_file, self.codecs['audio']))
                data['resolution_width'] = meta.get('resolution_width', 720)
                data['resolution_height'] = meta.get('resolution_height', 480)
                data['aspect'] = meta.get('resolution_width', 720) / meta.get('resolution_height', 480)
            except:
                log.debug('Error parsing metadata: %s %s' % (cur_file, traceback.format_exc()))
                pass

            if data.get('audio'): break

        data['quality'] = fireEvent('quality.guess', files = files, extra = data, single = True)
        if not data['quality']:
            data['quality'] = fireEvent('quality.single', 'dvdr' if group['is_dvd'] else 'dvdrip', single = True)

        data['quality_type'] = 'HD' if data.get('resolution_width', 0) >= 1280 else 'SD'

        filename = re.sub('(.cp\(tt[0-9{7}]+\))', '', files[0])
        data['group'] = self.getGroup(filename)
        data['source'] = self.getSourceMedia(filename)

        return data

    def getMeta(self, filename):

        try:
            p = enzyme.parse(filename)
            return {
                'video': p.video[0].codec,
                'audio': p.audio[0].codec,
                'resolution_width': tryInt(p.video[0].width),
                'resolution_height': tryInt(p.video[0].height),
            }
        except ParseError:
            log.debug('Failed to parse meta for %s' % filename)
        except NoParserError:
            log.debug('No parser found for %s' % filename)
        except:
            log.debug('Failed parsing %s' % filename)

        return {}

    def getSubtitleLanguage(self, group):
        detected_languages = {}

        # Subliminal scanner
        try:
            paths = group['files']['movie']
            scan_result = []
            for p in paths:
                if not group['is_dvd']:
                    scan_result.extend(scan(p))

            for video, detected_subtitles in scan_result:
                for s in detected_subtitles:
                    if s.language and s.path not in paths:
                        detected_languages[s.path] = [s.language]
        except:
            log.debug('Failed parsing subtitle languages for %s: %s' % (paths, traceback.format_exc()))

        # IDX
        for extra in group['files']['subtitle_extra']:
            try:
                if os.path.isfile(extra):
                    output = open(extra, 'r')
                    txt = output.read()
                    output.close()

                    idx_langs = re.findall('\nid: (\w+)', txt)

                    sub_file = '%s.sub' % os.path.splitext(extra)[0]
                    if len(idx_langs) > 0 and os.path.isfile(sub_file):
                        detected_languages[sub_file] = idx_langs
            except:
                log.error('Failed parsing subtitle idx for %s: %s' % (extra, traceback.format_exc()))

        return detected_languages

    def determineMovie(self, group):
        imdb_id = None

        files = group['files']

        # Check for CP(imdb_id) string in the file paths
        for cur_file in files['movie']:
            imdb_id = self.getCPImdb(cur_file)
            if imdb_id:
                log.debug('Found movie via CP tag: %s' % cur_file)
                break

        # Check and see if nfo contains the imdb-id
        if not imdb_id:
            try:
                for nfo_file in files['nfo']:
                    imdb_id = getImdb(nfo_file)
                    if imdb_id:
                        log.debug('Found movie via nfo file: %s' % nfo_file)
                        break
            except:
                pass

        # Check if path is already in db
        if not imdb_id:
            db = get_session()
            for cur_file in files['movie']:
                f = db.query(File).filter_by(path = toUnicode(cur_file)).first()
                try:
                    imdb_id = f.library[0].identifier
                    log.debug('Found movie via database: %s' % cur_file)
                    break
                except:
                    pass
            db.remove()

        # Search based on OpenSubtitleHash
        if not imdb_id and not group['is_dvd']:
            for cur_file in files['movie']:
                movie = fireEvent('movie.by_hash', file = cur_file, merge = True)

                if len(movie) > 0:
                    imdb_id = movie[0]['imdb']
                    if imdb_id:
                        log.debug('Found movie via OpenSubtitleHash: %s' % cur_file)
                        break

        # Search based on identifiers
        if not imdb_id:
            for identifier in group['identifiers']:

                if len(identifier) > 2:
                    try: filename = list(group['files'].get('movie'))[0]
                    except: filename = None
                    mdata = self.getReleaseNameYear(identifier, file_name = filename)
                    if 'name' in mdata:
                        movie = fireEvent('movie.search', q = '%(name)s %(year)s' % self.getReleaseNameYear(identifier, file_name = filename), merge = True, limit = 1)

                    if len(movie) > 0:
                        imdb_id = movie[0]['imdb']
                        log.debug('Found movie via search: %s' % cur_file)
                        if imdb_id: break
                else:
                    log.debug('Identifier to short to use for search: %s' % identifier)

        if imdb_id:
            return fireEvent('library.add', attrs = {
                'identifier': imdb_id
            }, update_after = False, single = True)

        log.error('No imdb_id found for %s.' % group['identifiers'])
        return {}

    def getCPImdb(self, string):

        try:
            m = re.search(self.cp_imdb, string.lower())
            id = m.group('id')
            if id:  return id
        except AttributeError:
            pass

        return False

    def removeCPTag(self, name):
        try:
            return re.sub(self.cp_imdb, '', name)
        except:
            pass
        return name

    def getSamples(self, files):
        return set(filter(lambda s: self.isSampleFile(s), files))

    def getMediaFiles(self, files):

        def test(s):
            return self.filesizeBetween(s, 300, 100000) and getExt(s.lower()) in self.extensions['movie'] and not self.isSampleFile(s)

        return set(filter(test, files))

    def getMovieExtras(self, files):
        return set(filter(lambda s: getExt(s.lower()) in self.extensions['movie_extra'], files))

    def getDVDFiles(self, files):
        def test(s):
            return self.isDVDFile(s)

        return set(filter(test, files))

    def getSubtitles(self, files):
        return set(filter(lambda s: getExt(s.lower()) in self.extensions['subtitle'], files))

    def getSubtitlesExtras(self, files):
        return set(filter(lambda s: getExt(s.lower()) in self.extensions['subtitle_extra'], files))

    def getNfo(self, files):
        return set(filter(lambda s: getExt(s.lower()) in self.extensions['nfo'], files))

    def getTrailers(self, files):

        def test(s):
            return re.search('(^|[\W_])trailer\d*[\W_]', s.lower()) and self.filesizeBetween(s, 2, 250)

        return set(filter(test, files))

    def getImages(self, files):

        def test(s):
            return getExt(s.lower()) in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tbn']
        files = set(filter(test, files))

        images = {}

        # Fanart
        images['backdrop'] = set(filter(lambda s: re.search('(^|[\W_])fanart|backdrop\d*[\W_]', s.lower()) and self.filesizeBetween(s, 0, 5), files))

        # Rest
        images['rest'] = files - images['backdrop']

        return images


    def isDVDFile(self, file_name):

        if list(set(file_name.lower().split(os.path.sep)) & set(['video_ts', 'audio_ts'])):
            return True

        for needle in ['vts_', 'video_ts', 'audio_ts', 'bdmv', 'certificate']:
            if needle in file_name.lower():
                return True

        return False

    def keepFile(self, filename):

        # ignoredpaths
        for i in self.ignored_in_path:
            if i in filename.lower():
                log.debug('Ignored "%s" contains "%s".' % (filename, i))
                return False

        # Sample file
        if self.isSampleFile(filename):
            log.debug('Is sample file "%s".' % filename)
            return False

        # Minimal size
        if self.filesizeBetween(filename, self.minimal_filesize['media']):
            log.debug('File to small: %s' % filename)
            return False

        # All is OK
        return True

    def isSampleFile(self, filename):
        is_sample = re.search('(^|[\W_])sample\d*[\W_]', filename.lower())
        if is_sample: log.debug('Is sample file: %s' % filename)
        return is_sample

    def filesizeBetween(self, file, min = 0, max = 100000):
        try:
            return (min * 1048576) < os.path.getsize(file) < (max * 1048576)
        except:
            log.error('Couldn\'t get filesize of %s.' % file)

        return False

    def createStringIdentifier(self, file_path, folder = '', exclude_filename = False):

        identifier = file_path.replace(folder, '') # root folder
        identifier = os.path.splitext(identifier)[0] # ext

        if exclude_filename:
            identifier = identifier[:len(identifier) - len(os.path.split(identifier)[-1])]

        # multipart
        identifier = self.removeMultipart(identifier)

        # remove cptag
        identifier = self.removeCPTag(identifier)

        # groups, release tags, scenename cleaner, regex isn't correct
        identifier = re.sub(self.clean, '::', simplifyString(identifier))

        # Year
        year = self.findYear(identifier)
        if year:
            identifier = '%s %s' % (identifier.split(year)[0].strip(), year)
        else:
            identifier = identifier.split('::')[0]

        # Remove duplicates
        out = []
        for word in identifier.split():
            if not word in out:
                out.append(word)

        identifier = ' '.join(out)

        return simplifyString(identifier)


    def removeMultipart(self, name):
        for regex in self.multipart_regex:
            try:
                found = re.sub(regex, '', name)
                if found != name:
                    name = found
            except:
                pass
        return name

    def getPartNumber(self, name):
        for regex in self.multipart_regex:
            try:
                found = re.search(regex, name)
                if found:
                    return found.group(1)
                return 1
            except:
                pass
        return 1

    def getCodec(self, filename, codecs):
        codecs = map(re.escape, codecs)
        try:
            codec = re.search('[^A-Z0-9](?P<codec>' + '|'.join(codecs) + ')[^A-Z0-9]', filename, re.I)
            return (codec and codec.group('codec')) or ''
        except:
            return ''

    def getGroup(self, file):
        try:
            match = re.search('-(?P<group>[A-Z0-9]+).', file, re.I)
            return match.group('group') or ''
        except:
            return ''

    def getSourceMedia(self, file):
        for media in self.source_media:
            for alias in self.source_media[media]:
                if alias in file.lower():
                    return media

        return None

    def findYear(self, text):
        matches = re.search('(?P<year>[12]{1}[0-9]{3})', text)
        if matches:
            return matches.group('year')

        return ''

    def getReleaseNameYear(self, release_name, file_name = None):

        # Use guessit first
        if file_name:
            try:
                guess = guess_movie_info(file_name)
                if guess.get('title') and guess.get('year'):
                    return {
                        'name': guess.get('title'),
                        'year': guess.get('year'),
                    }
            except:
                log.debug('Could not detect via guessit "%s": %s' % (file_name, traceback.format_exc()))

        # Backup to simple
        cleaned = ' '.join(re.split('\W+', simplifyString(release_name)))
        cleaned = re.sub(self.clean, ' ', cleaned)
        year = self.findYear(cleaned)

        if year: # Split name on year
            try:
                movie_name = cleaned.split(year).pop(0).strip()
                return {
                    'name': movie_name,
                    'year': int(year),
                }
            except:
                pass
        else: # Split name on multiple spaces
            try:
                movie_name = cleaned.split('  ').pop(0).strip()
                return {
                    'name': movie_name,
                    'year': int(year),
                }
            except:
                pass

        return {}
