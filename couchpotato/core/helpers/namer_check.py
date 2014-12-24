#Namer Check routine by sarakha63
from xml.dom.minidom import parseString
from xml.dom.minidom import Node
import cookielib
import urllib
import urllib2
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import getTitle, mergeDicts
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from dateutil.parser import parse
from guessit import guess_movie_info
from couchpotato.core.event import fireEvent

log = CPLog(__name__)

clean = '[ _\,\.\(\)\[\]\-](extended.cut|directors.cut|french|by|ioaw|swedisch|danish|dutch|swesub|spanish|german|ac3|dts|custom|dc|divx|divx5|dsr|dsrip|dutch|dvd|dvdr|dvdrip|dvdscr|dvdscreener|screener|dvdivx|cam|fragment|fs|hdtv|hdrip|hdtvrip|internal|limited|multisubs|ntsc|ogg|ogm|pal|pdtv|proper|repack|rerip|retail|r3|r5|bd5|se|svcd|swedish|german|read.nfo|nfofix|unrated|ws|telesync|ts|telecine|tc|brrip|bdrip|video_ts|audio_ts|480p|480i|576p|576i|720p|720i|1080p|1080i|hrhd|hrhdtv|hddvd|full|multi|bluray|x264|h264|xvid|xvidvd|xxx|www.www|cd[1-9]|\[.*\])([ _\,\.\(\)\[\]\-]|$)'
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
        
def correctName(check_name, movie):
        MovieTitles = movie['info']['titles']
        result=0
        for movietitle in MovieTitles:
            check_names = [simplifyString(check_name)]
    
            # Match names between "
            try: check_names.append(re.search(r'([\'"])[^\1]*\1', check_name).group(0))
            except: pass
    
            # Match longest name between []
            try: check_names.append(max(check_name.split('['), key = len))
            except: pass
    
            for check_name in list(set(check_names)):
                check_movie = getReleaseNameYear(check_name)
    
                try:
                    check_words = filter(None, re.split('\W+', simplifyString(check_movie.get('name', ''))))
                    movie_words = filter(None, re.split('\W+', simplifyString(movietitle)))
                    if len(check_words) > 0 and len(movie_words) > 0 and len(list(set(check_words) - set(movie_words))) == 0 and len(list(set(movie_words) - set(check_words))) == 0:
                        result+=1
                        return result
                except:
                    pass
    
            result+=0
        return result
    
def getReleaseNameYear(release_name, file_name = None):

        # Use guessit first
        guess = {}
        if release_name:
            release_name = re.sub(clean, ' ', release_name.lower())
            try:
                guess = guess_movie_info(toUnicode(release_name))
                if guess.get('title') and guess.get('year'):
                    guess = {
                        'name': guess.get('title'),
                        'year': guess.get('year'),
                    }
                elif guess.get('title'):
                    guess = {
                        'name': guess.get('title'),
                        'year': 0,
                    }
            except:
                log.debug('Could not detect via guessit "%s": %s', (file_name, traceback.format_exc()))

        # Backup to simple
        cleaned = ' '.join(re.split('\W+', simplifyString(release_name)))
        for i in range(1,4):
            cleaned = re.sub(clean, ' ', cleaned)
            cleaned = re.sub(clean, ' ', cleaned)
        year = findYear(cleaned)
        cp_guess = {}

        if year: # Split name on year
            try:
                movie_name = cleaned.split(year).pop(0).strip()
                cp_guess = {
                    'name': movie_name,
                    'year': int(year),
                }
            except:
                pass
        else: # Split name on multiple spaces
            try:
                movie_name = cleaned.split('  ').pop(0).strip()
                cp_guess = {
                    'name': movie_name,
                    'year': 0,
                }
            except:
                pass

        if cp_guess.get('year') == guess.get('year') and len(cp_guess.get('name', '')) > len(guess.get('name', '')):
            return guess
        elif guess == {}:
            return cp_guess
        if cp_guess.get('year') == guess.get('year') and len(cp_guess.get('name', '')) < len(guess.get('name', '')):
            return cp_guess
        return guess
    
def findYear(text):
        matches = re.search('(?P<year>19[0-9]{2}|20[0-9]{2})', text)
        if matches:
            return matches.group('year')

        return ''