from couchpotato.api import addApiView
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.environment import Env
from pytwitter import Api
from urlparse import parse_qsl
import oauth2

log = CPLog(__name__)


class Twitter(Notification):

    consumer_key = '3POVsO3KW90LKZXyzPOjQ'
    consumer_secret = 'Qprb94hx9ucXvD4Wvg2Ctsk4PDK7CcQAKgCELXoyIjE'

    request_token = None

    urls = {
        'request': 'https://api.twitter.com/oauth/request_token',
        'access': 'https://api.twitter.com/oauth/access_token',
        'authorize': 'https://api.twitter.com/oauth/authorize',
    }

    def __init__(self):
        super(Twitter, self).__init__()

        addApiView('notify.%s.auth_url' % self.getName().lower(), self.getAuthorizationUrl)
        addApiView('notify.%s.credentials' % self.getName().lower(), self.getCredentials)

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        api = Api(self.consumer_key, self.consumer_secret, self.conf('access_token_key'), self.conf('access_token_secret'))

        direct_message = self.conf('direct_message')
        direct_message_users = self.conf('screen_name')

        mention = self.conf('mention')
        mention_tag = None
        if mention:
            if direct_message:
                direct_message_users = '%s %s' % (direct_message_users, mention)
                direct_message_users = direct_message_users.replace('@', ' ')
                direct_message_users = direct_message_users.replace(',', ' ')
            else:
                mention_tag = '@%s' % mention.lstrip('@')
                message = '%s %s' % (message, mention_tag)

        try:
            if direct_message:
                for user in direct_message_users.split():
                    api.PostDirectMessage('[%s] %s' % (self.default_title, message), screen_name = user)
            else:
                update_message = '[%s] %s' % (self.default_title, message)
                if len(update_message) > 140:
                    if mention_tag:
                        api.PostUpdate(update_message[:135 - len(mention_tag)] + ('%s 1/2 ' % mention_tag))
                        api.PostUpdate(update_message[135 - len(mention_tag):] + ('%s 2/2 ' % mention_tag))
                    else:
                        api.PostUpdate(update_message[:135] + ' 1/2')
                        api.PostUpdate(update_message[135:] + ' 2/2')
                else:
                    api.PostUpdate(update_message)
        except Exception as e:
            log.error('Error sending tweet: %s', e)
            return False

        return True

    def getAuthorizationUrl(self, host = None, **kwargs):

        callback_url = cleanHost(host) + '%snotify.%s.credentials/' % (Env.get('api_base').lstrip('/'), self.getName().lower())

        oauth_consumer = oauth2.Consumer(self.consumer_key, self.consumer_secret)
        oauth_client = oauth2.Client(oauth_consumer)

        resp, content = oauth_client.request(self.urls['request'], 'POST', body = tryUrlencode({'oauth_callback': callback_url}))

        if resp['status'] != '200':
            log.error('Invalid response from Twitter requesting temp token: %s', resp['status'])
            return {
                'success': False,
            }
        else:
            self.request_token = dict(parse_qsl(content))

            auth_url = self.urls['authorize'] + ("?oauth_token=%s" % self.request_token['oauth_token'])

            log.info('Redirecting to "%s"', auth_url)
            return {
                'success': True,
                'url': auth_url,
            }

    def getCredentials(self, oauth_verifier, **kwargs):

        token = oauth2.Token(self.request_token['oauth_token'], self.request_token['oauth_token_secret'])
        token.set_verifier(oauth_verifier)

        oauth_consumer = oauth2.Consumer(key = self.consumer_key, secret = self.consumer_secret)
        oauth_client = oauth2.Client(oauth_consumer, token)

        resp, content = oauth_client.request(self.urls['access'], method = 'POST', body = 'oauth_verifier=%s' % oauth_verifier)
        access_token = dict(parse_qsl(content))

        if resp['status'] != '200':
            log.error('The request for an access token did not succeed: %s', resp['status'])
            return 'Twitter auth failed'
        else:
            log.debug('Tokens: %s, %s', (access_token['oauth_token'], access_token['oauth_token_secret']))

            self.conf('access_token_key', value = access_token['oauth_token'])
            self.conf('access_token_secret', value = access_token['oauth_token_secret'])
            self.conf('screen_name', value = access_token['screen_name'])

            self.request_token = None

            return 'redirect', Env.get('web_base') + 'settings/notifications/'
