from __future__ import with_statement
from blinker import signal, Signal
import ConfigParser
import os.path
import time


class Settings():

    on_save = Signal()
    on_register = Signal()

    bool = {'true':True, 'false':False}

    def setFile(self, file):
        self.file = file

        self.p = ConfigParser.RawConfigParser()
        self.p.read(file)

        from couchpotato.core.logger import CPLog
        self.log = CPLog(__name__)

        self.connectSignals()

    def parser(self):
        return self.p

    def sections(self):
        return self.p.sections()

    def connectSignals(self):
        signal('settings.register').connect(self.registerDefaults)
        signal('settings.save').connect(self.save)

    def registerDefaults(self, section_name, options = {}, save = True):

        self.addSection(section_name)
        for option, value in options.iteritems():
            self.setDefault(section_name, option, value)

        self.log.debug('Defaults for "%s": %s' % (section_name, options))
        self.on_register.send(self)

        if save:
            self.save(self)

    def set(self, section, option, value):
        return self.p.set(section, option, self.cleanValue(value))

    def get(self, option = '', section = 'global', default = ''):
        try:
            value = self.p.get(section, option)
            return self.cleanValue(value)
        except:
            return default

    def cleanValue(self, value):
        if(self.is_int(value)):
            return int(value)

        if str(value).lower() in self.bool:
            return self.bool.get(str(value).lower())

        return value.strip()

    def getValues(self):
        values = {}
        for section in self.sections():
            values[section] = {}
            for option in self.p.items(section):
                (option_name, option_value) = option
                values[section][option_name] = option_value
        return values

    def save(self, caller = ''):
        with open(self.file, 'wb') as configfile:
            self.p.write(configfile)

        self.log.debug('Saved settings')
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
