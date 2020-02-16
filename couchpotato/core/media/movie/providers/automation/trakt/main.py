import json
import traceback
import time

from couchpotato import Env, fireEvent
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import Provider
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)


class TraktBase(Provider):

    client_id = '8a54ed7b5e1b56d874642770ad2e8b73e2d09d6e993c3a92b1e89690bb1c9014'
    api_url = 'https://api-v2launch.trakt.tv/'

    def call(self, method_url, post_data = None):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % self.conf('automation_oauth_token'),
            'trakt-api-version': 2,
            'trakt-api-key': self.client_id,
        }

        if post_data:
            post_data = json.dumps(post_data)

        data = self.getJsonData(self.api_url + method_url, data = post_data or {}, headers = headers)
        return data if data else []


class Trakt(Automation, TraktBase):

    urls = {
        'watchlist': 'sync/watchlist/movies?extended=full',
        'oauth': 'https://api.couchpota.to/authorize/trakt/',
        'refresh_token': 'https://api.couchpota.to/authorize/trakt_refresh/',
    }

    def __init__(self):
        super(Trakt, self).__init__()

        addApiView('automation.trakt.auth_url', self.getAuthorizationUrl)
        addApiView('automation.trakt.credentials', self.getCredentials)

        fireEvent('schedule.interval', 'updater.check', self.refreshToken, hours = 24)
        addEvent('app.load', self.refreshToken)

    def refreshToken(self):

        token = self.conf('automation_oauth_token')
        refresh_token = self.conf('automation_oauth_refresh')
        if token and refresh_token:

            prop_name = 'last_trakt_refresh'
            last_refresh = int(Env.prop(prop_name, default = 0))

            if last_refresh < time.time()-4838400:  # refresh every 8 weeks
                log.debug('Refreshing trakt token')

                url = self.urls['refresh_token'] + '?token=' + self.conf('automation_oauth_refresh')
                data = fireEvent('cp.api_call', url, cache_timeout = 0, single = True)
                if data and 'oauth' in data and 'refresh' in data:
                    log.debug('Oauth refresh: %s', data)
                    self.conf('automation_oauth_token', value = data.get('oauth'))
                    self.conf('automation_oauth_refresh', value = data.get('refresh'))
                    Env.prop(prop_name, value = int(time.time()))
                else:
                    log.error('Failed refreshing Trakt token, please re-register in settings')

        elif token and not refresh_token:
            log.error('Refresh token is missing, please re-register Trakt for autorefresh of the token in the future')

    def getIMDBids(self):
        movies = []
        for movie in self.getWatchlist():
            m = movie.get('movie')
            m['original_title'] = m['title']
            log.debug("Movie: %s", m)
            if self.isMinimalMovie(m):
                log.info("Trakt automation: %s satisfies requirements, added", m.get('title'))
                movies.append(m.get('ids').get('imdb'))
                continue

        return movies

    def getWatchlist(self):
        return self.call(self.urls['watchlist'])

    def getAuthorizationUrl(self, host = None, **kwargs):
        callback_url = cleanHost(host) + '%sautomation.trakt.credentials/' % (Env.get('api_base').lstrip('/'))
        log.debug('callback_url is %s', callback_url)

        target_url = self.urls['oauth'] + "?target=" + callback_url
        log.debug('target_url is %s', target_url)

        return {
            'success': True,
            'url': target_url,
        }

    def getCredentials(self, **kwargs):
        try:
            oauth_token = kwargs.get('oauth')
            refresh_token = kwargs.get('refresh')

            log.debug('oauth_token is: %s', oauth_token)
            self.conf('automation_oauth_token', value = oauth_token)
            self.conf('automation_oauth_refresh', value = refresh_token)

            Env.prop('last_trakt_refresh', value = int(time.time()))
        except:
            log.error('Failed setting trakt token: %s', traceback.format_exc())

        return 'redirect', Env.get('web_base') + 'settings/automation/'
