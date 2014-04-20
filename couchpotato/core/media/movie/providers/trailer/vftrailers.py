from pygoogle import pygoogle
import subprocess
import time
import sys
import os.path
import unicodedata
import glob
import shutil
from couchpotato.core.media.movie.providers.trailer.base import VFTrailerProvider
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
log = CPLog(__name__)

autoload = 'vftrailers'

rootDir = os.path.dirname(os.path.abspath(__file__))
try:
    _DEV_NULL = subprocess.DEVNULL
except AttributeError:
    _DEV_NULL = open(os.devnull, 'wb')
class vftrailers(VFTrailerProvider):
    def search(self, group, filename, destination):
        movie_name = getTitle(group)
        movienorm = unicodedata.normalize('NFKD', movie_name).encode('ascii','ignore')
        movie_year = group['media']['info']['year']
        searchstring=movienorm+' '+ str(movie_year) +' bande annonce vf HD'
        time.sleep(3)
        log.info('Searching google for: %s', searchstring)
        g = pygoogle(str(searchstring))
        urllist = g.get_urls()
        cleanlist=[]
        for x in urllist:
            if 'youtube' in x or 'dailymotion' in x:
                cleanlist.append(x)
        if cleanlist:
            bocount=0
            for bo in cleanlist:
                if bocount==0:
                    tempdest=unicodedata.normalize('NFKD', os.path.join(rootDir,filename)).encode('ascii','ignore')+u'.%(ext)s'
                    log.info('Trying to download : %s to %s ', (bo, tempdest))
                    p=subprocess.Popen([sys.executable, 'youtube_dl/__main__.py', '-o',tempdest,'--newline', bo],cwd=rootDir, shell=False, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                    while p.poll() is None:
                        l = p.stdout.readline() # This blocks until it receives a newline.
                        lmsg= l.replace('%',' percent')+' '+filename
                        log.info(lmsg)
                    # When the subprocess terminates there might be unconsumed output 
                    # that still needs to be processed.
                    (out, err) = p.communicate()
                    outmsg='Out for '+filename +' : '+out
                    errmsg='Err for '+filename +' : '+err
                    if out:
                        log.info(outmsg)
                    if err:
                        log.info(errmsg)
                        continue
                    else:
                        listetemp=glob.glob(os.path.join(rootDir,'*'))
                        for listfile in listetemp:
                            if unicodedata.normalize('NFKD', filename).encode('ascii','ignore') in listfile:
                                ext=listfile[-4:]
                                finaldest=destination+ext
                                shutil.move(listfile, finaldest)
                                bocount=1
                                log.info('Downloaded trailer for : %s', movienorm)
                                return True
        else:
            return False
    
