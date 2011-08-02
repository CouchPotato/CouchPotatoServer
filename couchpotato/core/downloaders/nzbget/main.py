from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from tempfile import mkstemp
from urllib import urlencode
from xmlrpclib import ServerProxy, Error
import base64
import os
import re
import urllib2

log = CPLog(__name__)

class Nzbget(Downloader):

    type = ['nzb']

    def download(self, data = {}):
        if self.isDisabled() or not self.isCorrectType(data.get('type')):
            return
        
        if self.conf("host") == None:
            log.error(u"No NZBget host found in your configuration. Please configure it.")
            return False
        
        url = "http://nzbget:%s@%s/xmlrpc" % ( self.conf('password'), self.conf('host') )
        log.info("URL: %s" % url)
        log.info("Trying to establish a connection with %s" % (self.conf('host')))
        #log.info("Sending '%s' to NZBGet." % data.get('name'))
        
        try:
            req = ServerProxy(url)
            
            if req.writelog("INFO", "CouchPotato connected to drop of %s any moment now." % data.get('name')):
                log.info("Successfully connected to NZBget")
            else:
                log.error("Successfully connected to NZBget but unable to send a message.")
        except httplib.socket.error:
            log.error("Please check the configuration for NZBget. NZBget doesn't seem to respond to this combination of username and password." % e)
            
            return False
        except xmlrpclib.ProtocolError, e:
            if e.errormsg == "Unauthorized":
                log.error("The supplied password for NZBget is incorrect.")
            else:
                log.error("Protocol error: %s" % e.errormsg)
            
            return False
        except Exception, e:
            log.error("Unexpected exception. See: %s" % e.errormsg)
        
        try:
            nzbcontent = urllib2.urlopen(data.get('url'), timeout = 30)
        except Exception, e:
            log.error("Could not fetch the NZB-file from %s" % e)
            return False
        
        result = nzbcontent.read().strip();
        
        if not result:
            log.error("This NZB file is blank.")
            return False
        
        if not req.append(data.get('name'), self.conf('category'), False, base64.standard_b64encode(result)):
            log.error("NZBget could not add %s to the queue." % data.get('name'))
            return False
        
        return True
    
    def buildPp(self, imdb_id):

        pp_script_path = self.getPpFile()

        scriptB64 = '''IyEvdXNyL2Jpbi9weXRob24KaW1wb3J0IG9zCmltcG9ydCBzeXMKcHJpbnQgIkNyZWF0aW5nIGNwLmNw
bmZvIGZvciAlcyIgJSBzeXMuYXJndlsxXQppbWRiSWQgPSB7W0lNREJJREhFUkVdfQpwYXRoID0gb3Mu
cGF0aC5qb2luKHN5cy5hcmd2WzFdLCAiY3AuY3BuZm8iKQp0cnk6CiBmID0gb3BlbihwYXRoLCAndycp
CmV4Y2VwdCBJT0Vycm9yOgogcHJpbnQgIlVuYWJsZSB0byBvcGVuICVzIGZvciB3cml0aW5nIiAlIHBh
dGgKIHN5cy5leGl0KDEpCnRyeToKIGYud3JpdGUob3MucGF0aC5iYXNlbmFtZShzeXMuYXJndlswXSkr
IlxuIitpbWRiSWQpCmV4Y2VwdDoKIHByaW50ICJVbmFibGUgdG8gd3JpdGUgdG8gZmlsZTogJXMiICUg
cGF0aAogc3lzLmV4aXQoMikKZi5jbG9zZSgpCnByaW50ICJXcm90ZSBpbWRiIGlkLCAlcywgdG8gZmls
ZTogJXMiICUgKGltZGJJZCwgcGF0aCkK'''

        script = re.sub(r"\{\[IMDBIDHERE\]\}", "'%s'" % imdb_id, base64.b64decode(scriptB64))

        try:
            f = open(pp_script_path, 'wb')
        except:
            log.info("Unable to open post-processing script for writing. Check permissions: %s" % pp_script_path)
            return False

        try:
            f.write(script)
            f.close()
        except:
            log.info("Unable to write to post-processing script. Check permissions: %s" % pp_script_path)
            return False

        log.info("Wrote post-processing script to: %s" % pp_script_path)

        return os.path.basename(pp_script_path)

    def getPpFile(self):

        pp_script_handle, pp_script_path = mkstemp(suffix = '.py', dir = self.conf('ppDir'))
        pp_sh = os.fdopen(pp_script_handle)
        pp_sh.close()

        try:
            os.chmod(pp_script_path, int('777', 8))
        except:
            log.info("Unable to set post-processing script permissions to 777 (may still work correctly): %s" % pp_script_path)

        return pp_script_path