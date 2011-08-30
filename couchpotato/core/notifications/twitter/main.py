from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.environment import Env
from pytwitter import Api, parse_qsl
import oauth2
import urllib

log = CPLog(__name__)


class Twitter(Notification):

    consumer_key = "3POVsO3KW90LKZXyzPOjQ"
    consumer_secret = "Qprb94hx9ucXvD4Wvg2Ctsk4PDK7CcQAKgCELXoyIjE"

    urls = {
        'request': 'https://api.twitter.com/oauth/request_token',
        'access': 'https://api.twitter.com/oauth/access_token',
        'authorize': 'https://api.twitter.com/oauth/authorize',
    }

    def notify(self, message = '', data = {}):
        if self.isDisabled(): return

        api = Api(self.consumer_key, self.consumer_secret, self.conf('username'), self.conf('password'))

        try:
            api.PostUpdate('[%s] %s' % (self.default_title, message))
        except Exception, e:
            log.error('Error sending tweet: %s' % e)
            return False

        return True

    def getAuthorization(self, referer):

        oauth_consumer = oauth2.Consumer(self.consumer_key, self.consumer_secret)
        oauth_client = oauth2.Client(oauth_consumer)

        resp, content = oauth_client.request(self.url['request'], 'POST', body = urllib.urlencode({'oauth_callback': referer + 'twitterAuth/'}))

        if resp['status'] != '200':
            log.error('Invalid response from Twitter requesting temp token: %s' % resp['status'])
        else:
            request_token = dict(parse_qsl(content))

            Env.setting('username', section = 'twitter', value = request_token['oauth_token'])
            Env.setting('password', section = 'twitter', value = request_token['oauth_token_secret'])

            auth_url = self.url['authorize'] + "?oauth_token=" + request_token['oauth_token']

            log.info('Your Twitter authentication url is "%s"' % auth_url)
            return auth_url

    def getCredentials(self, key):
        request_token = {
            'oauth_token': self.conf('username'),
            'oauth_token_secret': self.conf('password'),
            'oauth_callback_confirmed': True
        }

        token = oauth2.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(key)

        log.info('Generating and signing request for an access token using key: %s' % key)

        oauth_consumer = oauth2.Consumer(key = self.consumer_key, secret = self.consumer_secret)
        oauth_client = oauth2.Client(oauth_consumer, token)

        resp, content = oauth_client.request(self.url['access'], method = 'POST', body = 'oauth_verifier=%s' % key)
        access_token = dict(parse_qsl(content))

        if resp['status'] != '200':
            log.error('The request for an access token did not succeed: ' + str(resp['status']))
            return False
        else:
            log.info('Your Twitter access token is %s' % access_token['oauth_token'])
            log.info('Access token secret is %s' % access_token['oauth_token_secret'])

            Env.setting('username', section = 'twitter', value = access_token['oauth_token'])
            Env.setting('password', section = 'twitter', value = access_token['oauth_token_secret'])

            return True
