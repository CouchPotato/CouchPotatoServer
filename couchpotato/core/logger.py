import logging
import re

class CPLog(object):

    context = ''
    replace_private = ['api', 'apikey', 'api_key', 'password', 'username', 'h']

    def __init__(self, context = ''):
        if context.endswith('.main'):
            context = context[:-5]

        self.context = context
        self.logger = logging.getLogger()

    def info(self, msg):
        self.logger.info(self.addContext(msg))

    def debug(self, msg):
        self.logger.debug(self.addContext(msg))

    def error(self, msg):
        self.logger.error(self.addContext(msg))

    def warning(self, msg):
        self.logger.warning(self.addContext(msg))

    def critical(self, msg):
        self.logger.critical(self.addContext(msg), exc_info = 1)

    def addContext(self, msg):
        return '[%+25.25s] %s' % (self.context[-25:], self.removePrivateData(msg))

    def removePrivateData(self, msg):
        try:
            msg = unicode(msg)
        except:
            pass

        from couchpotato.environment import Env
        if not Env.get('dev'):

            for replace in self.replace_private:
                msg = re.sub('(%s=)[^\&]+' % replace, '%s=xxx' % replace, msg)

            # Replace api key
            try:
                api_key = Env.setting('api_key')
                if api_key:
                    msg = msg.replace(api_key, 'API_KEY')
            except:
                pass

        return msg
