from couchpotato import app

class CPLog():

    context = ''

    def __init__(self, context = ''):
        self.context = context
        self.logger = app.logger

    def info(self, msg):
        self.logger.info(self.addContext(msg))

    def debug(self, msg):
        self.logger.debug(self.addContext(msg))

    def error(self, msg):
        self.logger.error(self.addContext(msg))

    def addContext(self, msg):
        return '[%+25.25s] %s' % (self.context[-25:], msg)
