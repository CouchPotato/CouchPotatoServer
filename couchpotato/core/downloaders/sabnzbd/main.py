from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from tempfile import mkstemp
from urllib import urlencode
import base64
import os
import re
import urllib2

log = CPLog(__name__)

class Sabnzbd(Downloader):

    type = ['nzb']

    def download(self, data = {}, movie = {}):

        if self.isDisabled() or not self.isCorrectType(data.get('type')):
            return

        log.info("Sending '%s' to SABnzbd." % data.get('name'))

        if self.conf('ppDir') and data.get('imdb_id'):
            try:
                pp_script_fn = self.buildPp(data.get('imdb_id'))
            except:
                log.info("Failed to create post-processing script.")
                pp_script_fn = False
            if not pp_script_fn:
                pp = False
            else:
                pp = True
        else:
            pp = False


        cp_tag = '.cp(' + movie['library'].get('identifier') + ')' if movie['library'].get('identifier') else ''
        params = {
            'apikey': self.conf('api_key'),
            'cat': self.conf('category'),
            'mode': 'addurl',
            'name': data.get('url'),
            'nzbname': '%s%s' % (data.get('name'), cp_tag),
        }

        # sabNzbd complains about "invalid archive file" for newzbin urls
        # added using addurl, works fine with addid
        if data.get('addbyid'):
            params['mode'] = 'addid'

        if pp:
            params['script'] = pp_script_fn

        url = cleanHost(self.conf('host')) + "api?" + urlencode(params)
        log.info("URL: " + url)

        try:
            r = urllib2.urlopen(url)
        except Exception, e:
            log.error("Unable to connect to SAB: %s" % e)
            return False

        result = r.read().strip()
        if not result:
            log.error("SABnzbd didn't return anything.")
            return False

        log.debug("Result text from SAB: " + result)
        if result == "ok":
            log.info("NZB sent to SAB successfully.")
            return True
        elif result == "Missing authentication":
            log.error("Incorrect username/password.")
            return False
        else:
            log.error("Unknown error: " + result)
            return False

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
