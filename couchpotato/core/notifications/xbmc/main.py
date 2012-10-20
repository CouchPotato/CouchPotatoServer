from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import base64

try: import simplejson as json
except ImportError: import json
  
import urllib2

log = CPLog(__name__)

class XBMCJSON:
    #below code is modified code from N3MIS15 on XBMC forum

    def __init__(self, server, user, password ):
        self.server = server
        self.version = '2.0'
        self.password = password
        self.user = user

    def Request(self, method, kwargs):
        data = [{}]
        data[0]['method'] = method
        data[0]['params'] = kwargs
        data[0]['jsonrpc'] = self.version
        data[0]['id'] = 1

        data = json.JSONEncoder().encode(data)
        content_length = len(data)

        content = {
            'Content-Type': 'application/json',
            'Content-Length': content_length,
        }
   
        request = urllib2.Request(self.server, data, content)
        base64string = base64.encodestring('%s:%s' % (self.user, self.password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)

        f = urllib2.urlopen(request)
        response = f.read()
        f.close()
        response = json.JSONDecoder().decode(response)
        print response

        try:
            return response[0]['result']
        except:
            return response[0]['error']



class XBMC(Notification):

    listen_to = ['movie.downloaded']

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        hosts = [x.strip() for x in self.conf('host').split(",")]
        successful = 0
        for host in hosts:
            xbmc = XBMCJSON('http://%s/jsonrpc' % host, self.conf('username'), self.conf('password'))
            if xbmc.Request("GUI.ShowNotification",{"title":"CouchPotato", "message":message}) == "OK":
                successful += 1
            if xbmc.Request("VideoLibrary.Scan",{}) == "OK": 
                successful += 1

        return successful == len(hosts)*2

