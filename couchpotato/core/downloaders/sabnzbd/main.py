from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from inspect import isfunction
from tempfile import mkstemp
import base64
import os
import re
import traceback

log = CPLog(__name__)

class Sabnzbd(Downloader):

    type = ['nzb']

    def download(self, data = {}, movie = {}, manual = False):

        if self.isDisabled(manual) or not self.isCorrectType(data.get('type')):
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

        params = {
            'apikey': self.conf('api_key'),
            'cat': self.conf('category'),
            'mode': 'addurl',
            'nzbname': self.createNzbName(data, movie),
        }

        if isfunction(data.get('download')):
            nzb_file = data.get('download')(url = data.get('url'), nzb_id = data.get('id'))

            if len(nzb_file) < 50:
                log.error('No nzb available!')
                return False

            # If it's a .rar, it adds the .rar extension, otherwise it stays .nzb
            nzb_filename = self.createFileName(data, nzb_file, movie)
            params['mode'] = 'addfile'
        else:
            params['name'] = data.get('url')

        if pp:
            params['script'] = pp_script_fn

        url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(params)

        try:
            if params.get('mode') is 'addfile':
                data = self.urlopen(url, params = {"nzbfile": (nzb_filename, nzb_file)}, multipart = True, show_error = False)
            else:
                data = self.urlopen(url, show_error = False)
        except:
            log.error(traceback.format_exc())
            return False

        result = data.strip()
        if not result:
            log.error("SABnzbd didn't return anything.")
            return False

        log.debug("Result text from SAB: " + result[:40])
        if result == "ok":
            log.info("NZB sent to SAB successfully.")
            return True
        elif result == "Missing authentication":
            log.error("Incorrect username/password.")
            return False
        else:
            log.error("Unknown error: " + result[:40])
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
