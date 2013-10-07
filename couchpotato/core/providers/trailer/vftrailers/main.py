from pygoogle import pygoogle
import subprocess
import time
import sys
import os.path
import unicodedata
from couchpotato.core.providers.trailer.base import VFTrailerProvider
from couchpotato.core.helpers.variable import mergeDicts, getTitle
from couchpotato.core.logger import CPLog
rootDir = os.path.dirname(os.path.abspath(__file__))
try:
    _DEV_NULL = subprocess.DEVNULL
except AttributeError:
    _DEV_NULL = open(os.devnull, 'wb')
class vftrailers(VFTrailerProvider):
    def search(self, group, filename, destination):
        movie_name = getTitle(group['library'])
        movienorm = unicodedata.normalize('NFKD', movie_name).encode('ascii','ignore')
        movie_year = group['library']['year']
        searchstring=movienorm+' '+ str(movie_year) +' bande annonce vf HD'
        time.sleep(3)
        g = pygoogle(str(searchstring))
        diclist = g.search()
        urllist = g.get_urls()
        cleanlist=[]
        for x in urllist:
            if 'youtube' in x or 'dailymotion' in x:
                cleanlist.append(x)
        if cleanlist:
            subprocess.check_call([sys.executable, 'youtube_dl/__main__.py', '-o',destination.encode('latin-1')+'.%(ext)s', cleanlist[0]], cwd=rootDir, shell=False, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            print process.communicate()
            return True
        else:
            return False
    
