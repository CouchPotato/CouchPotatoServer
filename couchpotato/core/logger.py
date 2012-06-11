import logging
import re
import traceback

class CPLog(object):

    context = ''
    replace_private = ['api', 'apikey', 'api_key', 'password', 'username', 'h']

    def __init__(self, context = ''):
        if context.endswith('.main'):
            context = context[:-5]

        self.context = context
        self.logger = logging.getLogger()

    def info(self, msg, replace_tuple = ()):
        self.logger.info(self.addContext(msg, replace_tuple))

    def debug(self, msg, replace_tuple = ()):
        self.logger.debug(self.addContext(msg, replace_tuple))

    def error(self, msg, replace_tuple = ()):
        self.logger.error(self.addContext(msg, replace_tuple))

    def warning(self, msg, replace_tuple = ()):
        self.logger.warning(self.addContext(msg, replace_tuple))

    def critical(self, msg, replace_tuple = ()):
        self.logger.critical(self.addContext(msg, replace_tuple), exc_info = 1)

    def addContext(self, msg, replace_tuple = ()):
        return '[%+25.25s] %s' % (self.context[-25:], self.safeMessage(msg, replace_tuple))

    def safeMessage(self, msg, replace_tuple = ()):

        if not hasattr(self, 'Env'):
            from couchpotato.environment import Env
            from couchpotato.core.helpers.encoding import toUnicode

            self.Env = Env
            self.toUnicode = toUnicode

        msg = self.toUnicode(msg)

        try:
            msg = msg % replace_tuple
        except:
            try:
                if isinstance(replace_tuple, tuple):
                    msg = msg % tuple([self.toUnicode(x).encode(self.Env.get('encoding')) for x in list(replace_tuple)])
                else:
                    msg = msg % self.toUnicode(replace_tuple).encode(self.Env.get('encoding'))
            except:
                self.error('Failed encoding stuff to log: %s' % traceback.format_exc())

        if not self.Env.get('dev'):

            for replace in self.replace_private:
                msg = re.sub('(%s=)[^\&]+' % replace, '%s=xxx' % replace, msg)

            # Replace api key
            try:
                api_key = self.Env.setting('api_key')
                if api_key:
                    msg = msg.replace(api_key, 'API_KEY')
            except:
                pass

        return msg
