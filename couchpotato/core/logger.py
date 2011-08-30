import logging

class CPLog():

    context = ''

    def __init__(self, context = ''):
        self.context = context
        self.logger = logging.getLogger()

        try:
            from couchpotato.environment import Env
            if Env.doDebug():
                import color_logs
        except:
            pass

    def info(self, msg):
        self.logger.info(self.addContext(msg))

    def debug(self, msg):
        self.logger.debug(self.addContext(msg))

    def error(self, msg):
        self.logger.error(self.addContext(msg))

    def critical(self, msg):
        self.logger.critical(self.addContext(msg), exc_info = 1)

    def addContext(self, msg):
        return '[%+25.25s] %s' % (self.context[-25:], msg)
