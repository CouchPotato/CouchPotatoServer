from couchpotato import get_session
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import File, Library, Release, Movie
from couchpotato.environment import Env
from flask.helpers import json
from themoviedb.tmdb import opensubtitleHashFile
import os
import re
import subprocess
import traceback

log = CPLog(__name__)


class Scanner(Plugin):

    minimal_filesize = {
        'media': 314572800, # 300MB
        'trailer': 1048576, # 1MB
    }
    ignored_in_path = ['_unpack', '_failed_', '_unknown_', '_exists_', '.appledouble', '.appledb', '.appledesktop', os.path.sep + '._', '.ds_store', 'cp.cpnfo'] #unpacking, smb-crap, hidden files
    ignore_names = ['extract', 'extracting', 'extracted', 'movie', 'movies', 'film', 'films']
    extensions = {
        'movie': ['mkv', 'wmv', 'avi', 'mpg', 'mpeg', 'mp4', 'm2ts', 'iso', 'img'],
        'dvd': ['vts_*', 'vob'],
        'nfo': ['nfo', 'txt', 'tag'],
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
        'video': ['x264', 'divx', 'xvid']
    }

    source_media = {
        'bluray': ['bluray', 'blu-ray', 'brrip', 'br-rip'],
        'hddvd': ['hddvd', 'hd-dvd'],
        'dvd': ['dvd'],
        'hdtv': ['hdtv']
    }

    clean = '(?i)[^\s](ac3|dts|custom|dc|divx|divx5|dsr|dsrip|dutch|dvd|dvdrip|dvdscr|dvdscreener|screener|dvdivx|cam|fragment|fs|hdtv|hdrip|hdtvrip|internal|limited|multisubs|ntsc|ogg|ogm|pal|pdtv|proper|repack|rerip|retail|r3|r5|bd5|se|svcd|swedish|german|read.nfo|nfofix|unrated|ws|telesync|ts|telecine|tc|brrip|bdrip|480p|480i|576p|576i|720p|720i|1080p|1080i|hrhd|hrhdtv|hddvd|bluray|x264|h264|xvid|xvidvd|xxx|www.www|cd[1-9]|\[.*\])[^\s]*'
    multipart_regex = [
        '[ _\.-]+cd[ _\.-]*([0-9a-d]+)', #*cd1
        '[ _\.-]+dvd[ _\.-]*([0-9a-d]+)', #*dvd1
        '[ _\.-]+part[ _\.-]*([0-9a-d]+)', #*part1.mkv
        '[ _\.-]+dis[ck][ _\.-]*([0-9a-d]+)', #*disk1.mkv
        '()[ _\.-]+([0-9]*[abcd]+)(\.....?)$',
        '([a-z])([0-9]+)(\.....?)$',
        '()([ab])(\.....?)$' #*a.mkv
    ]

    def __init__(self):

        addEvent('app.load', self.scan)

    def scan(self, folder = '/Volumes/Media/Test/'):

        """
        Get all files

        For each file larger then 350MB
            create movie "group", this is where all movie files will be grouped
            group multipart together
            check if its DVD (VIDEO_TS)

        # This should work for non-folder based structure
        for each moviegroup

            for each file smaller then 350MB, allfiles.filter(moviename*)

                # Assuming the beginning of the filename is the same for this structure
                Movie is masterfile, moviename-cd1.ext -> moviename
                    Find other files connected to moviename, moviename*.nfo, moviename*.sub, moviename*trailer.ext

                Remove found file from allfiles

            # This should work for folder based structure
            for each leftover file
                Loop over leftover files, use dirname as moviename


        For each found movie

            determine filetype

            Check if it's already in the db

            Add it to database
        """

        # Get movie "master" files
        movie_files = {}
        leftovers = []
        for root, dirs, files in os.walk(folder):
            for filename in files:

                file_path = os.path.join(root, filename)

                # Remove ignored files
                if not self.keepFile(file_path):
                    continue

                is_dvd_file = self.isDVDFile(file_path)
                if os.path.getsize(file_path) > self.minimal_filesize['media'] or is_dvd_file: # Minimal 300MB files or is DVD file

                    identifier = self.createFileIdentifier(file_path, folder, exclude_filename = is_dvd_file)

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

        # Open up the db
        db = get_session()

        # Mark all files as "offline" before a adding them to the database (again)
        files_in_path = db.query(File).filter(File.path.like(toUnicode(folder) + u'%%'))
        files_in_path.update({'available': 0}, synchronize_session = False)
        db.commit()

        # Determine file types
        update_after = []
        for identifier, group in movie_files.iteritems():

            # Group extra (and easy) files first
            images = self.getImages(group['unsorted_files'])
            group['files'] = {
                'subtitle': self.getSubtitles(group['unsorted_files']),
                'nfo': self.getNfo(group['unsorted_files']),
                'trailer': self.getTrailers(group['unsorted_files']),
                'backdrop': images['backdrop'],
                'leftover': set(group['unsorted_files']),
            }

            # Media files
            if group['is_dvd']:
                group['files']['movie'] = self.getDVDFiles(group['unsorted_files'])
            else:
                group['files']['movie'] = self.getMediaFiles(group['unsorted_files'])
                group['meta_data'] = self.getMetaData(group['files']['movie'])

            # Leftover "sorted" files
            for type in group['files']:
                group['files']['leftover'] -= set(group['files'][type])

            # Delete the unsorted list
            del group['unsorted_files']

            # Determine movie
            group['library'] = self.determineMovie(group)

            # Save to DB
            if group['library']:
                #library = db.query(Library).filter_by(id = library.get('id')).one()

                # Add release
                release = self.addRelease(group)
                return

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


    def addRelease(self, group):
        db = get_session()

        identifier = '%s.%s.%s' % (group['library']['identifier'], group['meta_data']['audio'], group['meta_data']['quality'])

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

        # Add release
        quality = fireEvent('quality.single', group['meta_data']['quality'], single = True)
        release = db.query(Release).filter_by(identifier = identifier).first()
        if not release:
            release = Release(
                identifier = identifier,
                movie = movie,
                quality_id = quality.get('id'),
                status_id = done_status.get('id')
            )
            db.add(release)
            db.commit()

        # Add each file type
        for type in group['files']:

            for file in group['files'][type]:
                added_file = self.saveFile(file, type = type, include_media_info = type is 'movie')
                try:
                    added_file = db.query(File).filter_by(id = added_file.get('id')).one()
                    release.files.append(added_file)
                    db.commit()
                except Exception, e:
                    log.debug('Failed to attach "%s" to release: %s' % (file, e))

        db.remove()

    def getMetaData(self, files):

        return {
            'audio': 'AC3',
            'quality': '720p',
            'quality_type': 'HD',
            'resolution_width': 1280,
            'resolution_height': 720
        }

        for file in files:
            self.getMeta(file)

    def getMeta(self, filename):
        lib_dir = os.path.join(Env.get('app_dir'), 'libs')
        script = os.path.join(lib_dir, 'getmeta.py')

        p = subprocess.Popen(["python", script, filename], stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = lib_dir)
        z = p.communicate()[0]

        try:
            meta = json.loads(z)
            log.info('Retrieved metainfo: %s' % meta)
            return meta
        except Exception, e:
            print e
            log.error('Couldn\'t get metadata from file')

    def determineMovie(self, group):
        imdb_id = None

        files = group['files']
        # Check and see if nfo contains the imdb-id
        try:
            for nfo_file in files['nfo']:
                imdb_id = self.getImdb(nfo_file)
                if imdb_id: break
        except:
            pass

        # Check if path is already in db
        db = get_session()
        for file in files['movie']:
            f = db.query(File).filter_by(path = toUnicode(file)).first()
            try:
                imdb_id = f.library[0].identifier
                break
            except:
                pass
        db.remove()

        # Search based on identifiers
        if not imdb_id:
            for identifier in group['identifiers']:
                if len(identifier) > 2:
                    movie = fireEvent('provider.movie.search', q = identifier, merge = True, limit = 1)
                    if len(movie) > 0:
                        imdb_id = movie[0]['imdb']
                        if imdb_id: break
                else:
                    log.debug('Identifier to short to use for search: %s' % identifier)

        if imdb_id:
            #movie = fireEvent('provider.movie.info', identifier = imdb_id, merge = True)
            #if movie and movie.get('imdb'):
            return fireEvent('library.add', attrs = {
                'identifier': imdb_id
            }, update_after = False, single = True)

        log.error('No imdb_id found for %s.' % group['identifiers'])
        return False

    def saveFile(self, file, type = 'unknown', include_media_info = False):

        properties = {}

        # Get media info for files
        if include_media_info:
            properties = {}

        # Check database and update/insert if necessary
        return fireEvent('file.add', path = file, part = self.getPartNumber(file), type = self.file_types[type], properties = properties, single = True)

    def getImdb(self, txt):

        if os.path.isfile(txt):
            output = open(txt, 'r')
            txt = output.read()
            output.close()

        try:
            m = re.search('(?P<id>tt[0-9{7}]+)', txt)
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

        for needle in ['vts_', 'video_ts', 'audio_ts']:
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
        return set(filter(lambda s:identifier in self.createFileIdentifier(s, folder), file_pile))

    def createFileIdentifier(self, file_path, folder, exclude_filename = False):
        identifier = file_path.replace(folder, '') # root folder
        identifier = os.path.splitext(identifier)[0] # ext
        if exclude_filename:
            identifier = identifier[:len(identifier) - len(os.path.split(identifier)[-1])]
        identifier = self.removeMultipart(identifier) # multipart

        return identifier

    def removeMultipart(self, name):
        for regex in self.multipart_regex:
            try:
                found = re.sub(regex, '', name)
                if found != name:
                    return found
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
