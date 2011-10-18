from couchpotato import get_session
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.helpers.variable import getExt, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import File
from couchpotato.environment import Env
from flask.helpers import json
import os
import re
import subprocess
import time
import traceback

log = CPLog(__name__)


class Scanner(Plugin):

    minimal_filesize = {
        'media': 314572800, # 300MB
        'trailer': 1048576, # 1MB
    }
    ignored_in_path = ['_unpack', '_failed_', '_unknown_', '_exists_', '.appledouble', '.appledb', '.appledesktop', os.path.sep + '._', '.ds_store', 'cp.cpnfo'] #unpacking, smb-crap, hidden files
    ignore_names = ['extract', 'extracting', 'extracted', 'movie', 'movies', 'film', 'films', 'download', 'downloads', 'video_ts', 'audio_ts', 'bdmv', 'certificate']
    extensions = {
        'movie': ['mkv', 'wmv', 'avi', 'mpg', 'mpeg', 'mp4', 'm2ts', 'iso', 'img'],
        'dvd': ['vts_*', 'vob'],
        'nfo': ['nfo', 'nfo-orig', 'txt', 'tag'],
        'subtitle': ['sub', 'srt', 'ssa', 'ass'],
        'subtitle_extra': ['idx'],
        'trailer': ['mov', 'mp4', 'flv']
    }
    file_types = {
        'subtitle': ('subtitle', 'subtitle'),
        'trailer': ('video', 'trailer'),
        'nfo': ('nfo', 'nfo'),
        'movie': ('video', 'movie'),
        'backdrop': ('image', 'backdrop'),
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

    clean = '[ _\,\.\(\)\[\]\-](french|swedisch|danish|dutch|swesub|spanish|german|ac3|dts|custom|dc|divx|divx5|dsr|dsrip|dutch|dvd|dvdrip|dvdscr|dvdscreener|screener|dvdivx|cam|fragment|fs|hdtv|hdrip|hdtvrip|internal|limited|multisubs|ntsc|ogg|ogm|pal|pdtv|proper|repack|rerip|retail|r3|r5|bd5|se|svcd|swedish|german|read.nfo|nfofix|unrated|ws|telesync|ts|telecine|tc|brrip|bdrip|video_ts|audio_ts|480p|480i|576p|576i|720p|720i|1080p|1080i|hrhd|hrhdtv|hddvd|bluray|x264|h264|xvid|xvidvd|xxx|www.www|cd[1-9]|\[.*\])([ _\,\.\(\)\[\]\-]|$)'
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

    def __init__(self):

        addEvent('scanner.create_file_identifier', self.createStringIdentifier)

        addEvent('scanner.scan', self.scan)
        addEvent('scanner.files', self.scanToFilesLibrary)
        addEvent('scanner.folder', self.scanToFolderLibrary)
        addEvent('scanner.name_year', self.getReleaseNameYear)

    def scanToFilesLibrary(self, folder = None, files = None):

        groups = self.scan(folder = folder, files = files)

        for group in groups.itervalues():
            if group['library']:
                fireEvent('release.add', group = group)

    def scanToFolderLibrary(self, folder = None):

        if not os.path.isdir(folder):
            return

        groups = self.scan(folder = folder)

        # Open up the db
        db = get_session()

        # Mark all files as "offline" before a adding them to the database (again)
        files_in_path = db.query(File).filter(File.path.like(toUnicode(folder) + u'%%'))
        files_in_path.update({'available': 0}, synchronize_session = False)
        db.commit()

        update_after = []
        for group in groups.itervalues():

            # Save to DB
            if group['library']:
                #library = db.query(Library).filter_by(id = library.get('id')).one()

                # Add release
                fireEvent('release.add', group = group)

                # Add identifier for library update
                update_after.append(group['library'].get('identifier'))

        for identifier in update_after:
            fireEvent('library.update', identifier = identifier)

        # If cleanup option is enabled, remove offline files from database
        if self.conf('cleanup_offline'):
            files_in_path = db.query(File).filter(File.path.like(folder + '%%')).filter_by(available = 0)
            [db.delete(x) for x in files_in_path]
            db.commit()

        db.remove()


    def scan(self, folder = None, files = []):

        if not folder or not os.path.isdir(folder):
            log.error('Folder doesn\'t exists: %s' % folder)
            return {}

        # Get movie "master" files
        movie_files = {}
        leftovers = []

        # Scan all files of the folder if no files are set
        if len(files) == 0:
            files = []
            for root, dirs, walk_files in os.walk(folder):
                for filename in walk_files:
                    files.append(os.path.join(root, filename))

        for file_path in files:

            # Remove ignored files
            if not self.keepFile(file_path):
                continue

            is_dvd_file = self.isDVDFile(file_path)
            if os.path.getsize(file_path) > self.minimal_filesize['media'] or is_dvd_file: # Minimal 300MB files or is DVD file

                identifier = self.createStringIdentifier(file_path, folder, exclude_filename = is_dvd_file)

                if not movie_files.get(identifier):
                    movie_files[identifier] = {
                        'unsorted_files': [],
                        'identifiers': [],
                        'is_dvd': is_dvd_file,
                    }

                movie_files[identifier]['unsorted_files'].append(file_path)
            else:
                leftovers.append(file_path)

        # Sort reverse, this prevents "Iron man 2" from getting grouped with "Iron man" as the "Iron Man 2"
        # files will be grouped first.
        leftovers = set(sorted(leftovers, reverse = True))

        id_handles = [
            None, # Attach files to group by identifier
            lambda x: os.path.split(x)[-1], # Attach files via filename of master_file name only
            os.path.dirname, # Attach files via master_file dirname
        ]

        # Create identifier based on handle
        for handler in id_handles:
            for identifier, group in movie_files.iteritems():
                identifier = handler(identifier) if handler else identifier
                if identifier not in group['identifiers'] and len(identifier) > 0: group['identifiers'].append(identifier)

                # Group the files based on the identifier
                found_files = self.getGroupFiles(identifier, folder, leftovers)
                group['unsorted_files'].extend(found_files)

                # Remove the found files from the leftover stack
                leftovers = leftovers - found_files


        # Determine file types
        delete_identifier = []
        for identifier in movie_files:
            group = movie_files[identifier]

            # Check if movie is fresh and maybe still unpacking, ignore files new then 1 minute
            file_too_new = False
            for file in group['unsorted_files']:
                if os.path.getmtime(file) > time.time() - 60:
                    file_too_new = True

            if file_too_new:
                log.info('Files seem to be still unpacking or just unpacked, ignoring for now: %s' % identifier)
                delete_identifier.append(identifier)
                continue

            # Group extra (and easy) files first
            images = self.getImages(group['unsorted_files'])
            group['files'] = {
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
            group['meta_data'] = self.getMetaData(group)

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
            for type in group['files']:
                if not type is 'leftover':
                    group['files']['leftover'] -= set(group['files'][type])

            # Delete the unsorted list
            del group['unsorted_files']

            # Determine movie
            group['library'] = self.determineMovie(group)
            if not group['library']:
                log.error('Unable to determin movie: %s' % group['identifiers'])

        # Delete still (asuming) unpacking files
        for identifier in delete_identifier:
            del movie_files[identifier]

        return movie_files

    def getMetaData(self, group):

        data = {}
        files = list(group['files']['movie'])

        for file in files:
            if os.path.getsize(file) < self.minimal_filesize['media']: continue # Ignore smaller files

            meta = self.getMeta(file)

            try:
                data['video'] = self.getCodec(file, self.codecs['video'])
                data['audio'] = meta['audio stream'][0]['compression']
                data['resolution_width'] = meta['video stream'][0]['image width']
                data['resolution_height'] = meta['video stream'][0]['image height']
            except:
                pass

            if data.get('audio'): break

        data['quality'] = fireEvent('quality.guess', files = files, extra = data, single = True)
        if not data['quality']:
            data['quality'] = fireEvent('quality.single', 'dvdr' if group['is_dvd'] else 'dvdrip', single = True)

        data['quality_type'] = 'HD' if data.get('resolution_width', 0) >= 1280 else 'SD'

        file = re.sub('(.cp\(tt[0-9{7}]+\))', '', files[0])
        data['group'] = self.getGroup(file)
        data['source'] = self.getSourceMedia(file)

        return data

    def getMeta(self, filename):
        lib_dir = os.path.join(Env.get('app_dir'), 'libs')
        script = os.path.join(lib_dir, 'getmeta.py')

        p = subprocess.Popen(["python", script, filename], stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = lib_dir)
        z = p.communicate()[0]

        try:
            meta = json.loads(z)
            return meta
        except Exception:
            log.error('Couldn\'t get metadata from file: %s' % traceback.format_exc())

    def determineMovie(self, group):
        imdb_id = None

        files = group['files']

        # Check for CP(imdb_id) string in the file paths
        for file in files['movie']:
            imdb_id = self.getCPImdb(file)
            if imdb_id: break

        # Check and see if nfo contains the imdb-id
        if not imdb_id:
            try:
                for nfo_file in files['nfo']:
                    imdb_id = getImdb(nfo_file)
                    if imdb_id: break
            except:
                pass

        # Check if path is already in db
        if not imdb_id:
            db = get_session()
            for file in files['movie']:
                f = db.query(File).filter_by(path = toUnicode(file)).first()
                try:
                    imdb_id = f.library[0].identifier
                    break
                except:
                    pass
            db.remove()

        # Search based on OpenSubtitleHash
        if not imdb_id and not group['is_dvd']:
            for file in files['movie']:
                movie = fireEvent('movie.by_hash', file = file, merge = True)

                if len(movie) > 0:
                    imdb_id = movie[0]['imdb']
                    if imdb_id: break

        # Search based on identifiers
        if not imdb_id:
            for identifier in group['identifiers']:

                if len(identifier) > 2:

                    movie = fireEvent('movie.search', q = identifier, merge = True, limit = 1)

                    if len(movie) > 0:
                        imdb_id = movie[0]['imdb']
                        if imdb_id: break
                else:
                    log.debug('Identifier to short to use for search: %s' % identifier)

        if imdb_id:
            #movie = fireEvent('movie.info', identifier = imdb_id, merge = True)
            #if movie and movie.get('imdb'):
            return fireEvent('library.add', attrs = {
                'identifier': imdb_id
            }, update_after = False, single = True)

        log.error('No imdb_id found for %s.' % group['identifiers'])
        return {}

    def getCPImdb(self, string):

        try:
            m = re.search('(cp\((?P<id>tt[0-9{7}]+)\))', string.lower())
            id = m.group('id')
            if id:  return id
        except AttributeError:
            pass

        return False

    def getMediaFiles(self, files):

        def test(s):
            return self.filesizeBetween(s, 300, 100000) and getExt(s.lower()) in self.extensions['movie']

        return set(filter(test, files))

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


    def isDVDFile(self, file):

        if list(set(file.lower().split(os.path.sep)) & set(['video_ts', 'audio_ts'])):
            return True

        for needle in ['vts_', 'video_ts', 'audio_ts', 'bdmv', 'certificate']:
            if needle in file.lower():
                return True

        return False

    def keepFile(self, file):

        # ignoredpaths
        for i in self.ignored_in_path:
            if i in file.lower():
                log.debug('Ignored "%s" contains "%s".' % (file, i))
                return False

        # Sample file
        if re.search('(^|[\W_])sample\d*[\W_]', file.lower()):
            log.debug('Is sample file "%s".' % file)
            return False

        # Minimal size
        if self.filesizeBetween(file, self.minimal_filesize['media']):
            log.debug('File to small: %s' % file)
            return False

        # All is OK
        return True


    def filesizeBetween(self, file, min = 0, max = 100000):
        try:
            return (min * 1048576) < os.path.getsize(file) < (max * 1048576)
        except:
            log.error('Couldn\'t get filesize of %s.' % file)

        return False

    def getGroupFiles(self, identifier, folder, file_pile):
        return set(filter(lambda s:identifier in self.createStringIdentifier(s, folder), file_pile))

    def createStringIdentifier(self, file_path, folder = '', exclude_filename = False):

        identifier = file_path.replace(folder, '') # root folder
        identifier = os.path.splitext(identifier)[0] # ext

        if exclude_filename:
            identifier = identifier[:len(identifier) - len(os.path.split(identifier)[-1])]

        # multipart
        identifier = self.removeMultipart(identifier)

        # groups, release tags, scenename cleaner, regex isn't correct
        identifier = re.sub(self.clean, '::', simplifyString(identifier))

        # Year
        year = self.findYear(identifier)
        if year:
            identifier = '%s %s' % (identifier.split(year)[0].strip(), year)
        else:
            identifier = identifier.split('::')[0]

        # Quality
        quality = fireEvent('quality.guess', [file_path], single = True)
        identifier += ' %s' % quality.get('identifier', '')

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
        return name

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
        matches = re.search('(?P<year>[0-9]{4})', text)
        if matches:
            return matches.group('year')

        return ''

    def getReleaseNameYear(self, release_name):
        cleaned = ' '.join(re.split('\W+', simplifyString(release_name)))
        cleaned = re.sub(self.clean, ' ', cleaned)
        year = self.findYear(cleaned)

        if year: # Split name on year
            try:
                movie_name = cleaned.split(year).pop(0).strip()
                return {
                    'name': movie_name,
                    'year': year,
                }
            except:
                pass
        else: # Split name on multiple spaces
            try:
                movie_name = cleaned.split('  ').pop(0).strip()
                return {
                    'name': movie_name,
                    'year': year,
                }
            except:
                pass

        return {}
