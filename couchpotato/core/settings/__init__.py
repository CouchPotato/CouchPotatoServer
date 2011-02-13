from __future__ import with_statement
from blinker import signal, Signal
from couchpotato.core.logger import CPLog
import ConfigParser
import os.path
import time

log = CPLog(__name__)

class Settings():

    on_save = Signal()
    on_register = Signal()

    bool = {'true':True, 'false':False}

    def __init__(self):

        # Connect signals
        signal('settings.register').connect(self.registerDefaults)
        signal('settings.save').connect(self.save)

    def setFile(self, file):
        self.file = file

        self.p = ConfigParser.RawConfigParser()
        self.p.read(file)

    def parser(self):
        return self.p

    def sections(self):
        return self.s

    def registerDefaults(self, section_name, options = {}, save = True):

        self.addSection(section_name)
        for option, value in options.iteritems():
            self.setDefault(section_name, option, value)

        log.debug('Defaults for "%s": %s' % (section_name, options))
        self.on_register.send(self)

        if save:
            self.save(self)

    def set(self, section, option, value):
        return self.p.set(section, option, value)

    def get(self, option = '', section = 'global', default = ''):

        try:
            value = self.p.get(section, option)

            if(self.is_int(value)):
                return int(value)

            if str(value).lower() in self.bool:
                return self.bool.get(str(value).lower())

            return value if type(value) != str else value.strip()
        except:
            return default

    def save(self, caller):
        with open(self.file, 'wb') as configfile:
            self.p.write(configfile)

        log.debug('Saved settings')
        self.on_save.send(self)

    def addSection(self, section):
        if not self.p.has_section(section):
            self.p.add_section(section)

    def setDefault(self, section, option, value):
        if not self.p.has_option(section, option):
            self.p.set(section, option, value)

    def is_int(self, value):
        try:
            int(value)
            return True
        except ValueError:
            return False

settings = Settings()
