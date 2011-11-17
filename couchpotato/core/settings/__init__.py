from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.helpers.request import getParams, jsonified
from couchpotato.core.helpers.variable import mergeDicts
import ConfigParser
import os.path
import time
import re


class Settings():

    txt_to_type = {
        'str'    : str,
        'unicode': unicode,
        'int'    : int,
        'bool'   : bool,
    }
    type_re = re.compile("(%s)\((.*)\)$" 
                         % ("|".join(txt_to_type.keys())))
    options = {}

    def __init__(self):

        addApiView('settings', self.view)
        addApiView('settings.save', self.saveView)

    def setFile(self, file):
        self.file = file

        self.p = ConfigParser.RawConfigParser()
        self.p.read(file)

        from couchpotato.core.logger import CPLog
        self.log = CPLog(__name__)

        self.connectEvents()

    def parser(self):
        return self.p

    def sections(self):
        return self.p.sections()

    def connectEvents(self):
        addEvent('settings.options', self.addOptions)
        addEvent('settings.register', self.registerDefaults)
        addEvent('settings.save', self.save)

    def registerDefaults(self, section_name, options = {}, save = True):
        self.addSection(section_name)
        for option, value in options.iteritems():
            self.setDefault(section_name, option, value)

        #self.log.debug('Defaults for "%s": %s' % (section_name, options))

        if save:
            self.save(self)

    def set(self, section, option, value):
        # Makes sure i won't change type!
        old_value = self.get(option, section, None)
        if None != old_value:
            value = type(old_value)(value)
        
        return self.p.set(section, option, self.encodeValue(value))

    def get(self, option = '', section = 'core', default = ''):
        try:
            value = self.p.get(section, option)
            return self.decodeValue(value)
        except:
            return default

    def encodeValue(self, value):
        if hasattr(value, "strip"):
            value = value.strip()
        
        for type_name, type_cast in self.txt_to_type.iteritems():
            if type(value) is type_cast:
                return "%s(%s)" % (type_name, value)
        return None
    
    def decodeValue(self, value):
        (type, val) = self.type_re.findall(value)[0]
        val = self.txt_to_type[type](val)
        return val

    def getValues(self):
        values = {}
        for section in self.sections():
            values[section] = {}
            for option in self.p.items(section):
                (option_name, option_value) = option
                values[section][option_name] = self.decodeValue(option_value)
        return values

    def save(self):
        with open(self.file, 'wb') as configfile:
            self.p.write(configfile)

        self.log.debug('Saved settings')

    def addSection(self, section):
        if not self.p.has_section(section):
            self.p.add_section(section)

    def setDefault(self, section, option, value):
        if not self.p.has_option(section, option):
            self.set(section, option, value)

    def addOptions(self, section_name, options):

        if not self.options.get(section_name):
            self.options[section_name] = options
        else:
            options['groups'] = self.options[section_name].get('groups') + options.get('groups')
            self.options[section_name] = mergeDicts(self.options[section_name], options)

    def getOptions(self):
        return self.options


    def view(self):

        return jsonified({
            'options': self.getOptions(),
            'values': self.getValues()
        })

    def saveView(self):

        params = getParams()

        section = params.get('section')
        option = params.get('name')
        value = params.get('value')
        
        self.set(section, option, value)
        self.save()

        return jsonified({
            'success': True,
        })
