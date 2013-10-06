from pygoogle import pygoogle
import subprocess
import time
import sys
import os.path
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
        movie_year = group['library']['year']
        searchstring=movie_name +' '+ str(movie_year) +' bande annonce vf HD'
        time.sleep(3)
        g = pygoogle(searchstring)
        urllist = g.get_urls()
        cleanlist=[]
        for x in urllist:
            if 'youtube' in x or 'dailymotion' in x:
                cleanlist.append(x)
        if cleanlist:
            subprocess.check_call([sys.executable, 'youtube_dl/__main__.py', '-o',destination+'.%(ext)s', cleanlist[0]], cwd=rootDir, stdout=_DEV_NULL)
            return True
        else:
            return False
    
