import json
import httplib
import urllib2
from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import YarrProvider
from urllib2 import Request

log = CPLog(__name__)

class OCHProvider(YarrProvider):

    protocol = 'och'

    def download(self, url = '', nzb_id = ''):
        return url