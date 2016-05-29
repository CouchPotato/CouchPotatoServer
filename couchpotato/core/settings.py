from __future__ import with_statement
import ConfigParser
import traceback
from hashlib import md5

from CodernityDB.hash_index import HashIndex
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import mergeDicts, tryInt, tryFloat

class Settings(object):

    options = {}
    types = {}

    def __init__(self):

        addApiView('settings', self.view, docs = {
            'desc': 'Return the options and its values of settings.conf. Including the default values and group ordering used on the settings page.',
            'return': {'type': 'object', 'example': """{
    // objects like in __init__.py of plugin
    "options": {
        "moovee" : {
            "groups" : [{
                "description" : "SD movies only",
                "name" : "#alt.binaries.moovee",
                "options" : [{
                    "default" : false,
                    "name" : "enabled",
                    "type" : "enabler"
                }],
                "tab" : "providers"
            }],
            "name" : "moovee"
        }
    },
    // object structured like settings.conf
    "values": {
        "moovee": {
            "enabled": false
        }
    }
}"""}
        })

        addApiView('settings.save', self.saveView, docs = {
            'desc': 'Save setting to config file (settings.conf)',
            'params': {
                'section': {'desc': 'The section name in settings.conf'},
                'name': {'desc': 'The option name'},
                'value': {'desc': 'The value you want to save'},
            }
        })

        addEvent('database.setup', self.databaseSetup)

        self.file = None
        self.p = None
        self.log = None
        self.directories_delimiter = "::"

    def setFile(self, config_file):
        self.file = config_file

        self.p = ConfigParser.RawConfigParser()
        self.p.read(config_file)

        from couchpotato.core.logger import CPLog
        self.log = CPLog(__name__)

        self.connectEvents()

    def databaseSetup(self):
        fireEvent('database.setup_index', 'property', PropertyIndex)

    def parser(self):
        return self.p

    def sections(self):
        res = filter( self.isSectionReadable, self.p.sections())
        return res

    def connectEvents(self):
        addEvent('settings.options', self.addOptions)
        addEvent('settings.register', self.registerDefaults)
        addEvent('settings.save', self.save)

    def registerDefaults(self, section_name, options = None, save = True):
        if not options: options = {}

        self.addSection(section_name)

        for option_name, option in options.items():
            self.setDefault(section_name, option_name, option.get('default', ''))

            # Set UI-meta for option (hidden/ro/rw)
            if option.get('ui-meta'):
                value = option.get('ui-meta')
                if value:
                    value = value.lower()
                    if value in ['hidden', 'rw', 'ro']:
                        meta_option_name = option_name + self.optionMetaSuffix()
                        self.setDefault(section_name, meta_option_name, value)
                    else:
                        self.log.warning('Wrong value for option %s.%s : ui-meta can not be equal to "%s"', (section_name, option_name, value))

            # Migrate old settings from old location to the new location
            if option.get('migrate_from'):
                if self.p.has_option(option.get('migrate_from'), option_name):
                    previous_value = self.p.get(option.get('migrate_from'), option_name)
                    self.p.set(section_name, option_name, previous_value)
                    self.p.remove_option(option.get('migrate_from'), option_name)

            if option.get('type'):
                self.setType(section_name, option_name, option.get('type'))

        if save:
            self.save()

    def set(self, section, option, value):
        if not self.isOptionWritable(section, option):
            self.log.warning('set::option "%s.%s" isn\'t writable', (section, option))
            return None
        if self.isOptionMeta(section, option):
            self.log.warning('set::option "%s.%s" cancelled, since it is a META option', (section, option))
            return None

        return self.p.set(section, option, value)

    def get(self, option = '', section = 'core', default = None, type = None):
        if self.isOptionMeta(section, option):
            self.log.warning('get::option "%s.%s" cancelled, since it is a META option', (section, option))
            return None

        tp = type
        try:
            tp = self.getType(section, option) if not tp else tp

            if hasattr(self, 'get%s' % tp.capitalize()):
                return getattr(self, 'get%s' % tp.capitalize())(section, option)
            else:
                return self.getUnicode(section, option)

        except:
            return default

    def delete(self, option = '', section = 'core'):
        if not self.isOptionWritable(section, option):
            self.log.warning('delete::option "%s.%s" isn\'t writable', (section, option))
            return None

        if self.isOptionMeta(section, option):
            self.log.warning('set::option "%s.%s" cancelled, since it is a META option', (section, option))
            return None

        self.p.remove_option(section, option)
        self.save()

    def getEnabler(self, section, option):
        return self.getBool(section, option)

    def getBool(self, section, option):
        try:
            return self.p.getboolean(section, option)
        except:
            return self.p.get(section, option) == 1

    def getInt(self, section, option):
        try:
            return self.p.getint(section, option)
        except:
            return tryInt(self.p.get(section, option))

    def getFloat(self, section, option):
        try:
            return self.p.getfloat(section, option)
        except:
            return tryFloat(self.p.get(section, option))

    def getDirectories(self, section, option):
        value = self.p.get(section, option)

        if value:
            return map(str.strip, str.split(value, self.directories_delimiter))
        return []

    def getUnicode(self, section, option):
        value = self.p.get(section, option).decode('unicode_escape')
        return toUnicode(value).strip()

    def getValues(self):
        from couchpotato.environment import Env

        values = {}
        soft_chroot = Env.get('softchroot')

        # TODO : There is two commented "continue" blocks (# COMMENTED_SKIPPING). They both are good...
        #        ... but, they omit output of values of hidden and non-readable options
        #        Currently, such behaviour could break the Web UI of CP...
        #        So, currently this two blocks are commented (but they are required to
        #        provide secure hidding of options.
        for section in self.sections():

            # COMMENTED_SKIPPING
            #if not self.isSectionReadable(section):
            #    continue

            values[section] = {}
            for option in self.p.items(section):
                (option_name, option_value) = option

                #skip meta options:
                if self.isOptionMeta(section, option_name):
                    continue

                # COMMENTED_SKIPPING
                #if not self.isOptionReadable(section, option_name):
                #    continue

                value = self.get(option_name, section)

                is_password = self.getType(section, option_name) == 'password'
                if is_password and value:
                    value = len(value) * '*'

                # chrootify directory before sending to UI:
                if (self.getType(section, option_name) == 'directory') and value:
                    try: value = soft_chroot.abs2chroot(value)
                    except: value = ""
                # chrootify directories before sending to UI:
                if (self.getType(section, option_name) == 'directories'):
                    if (not value):
                        value = []
                    try : value = map(soft_chroot.abs2chroot, value)
                    except : value = []

                values[section][option_name] = value

        return values

    def save(self):
        with open(self.file, 'wb') as configfile:
            self.p.write(configfile)

    def addSection(self, section):
        if not self.p.has_section(section):
            self.p.add_section(section)

    def setDefault(self, section, option, value):
        if not self.p.has_option(section, option):
            self.p.set(section, option, value)

    def setType(self, section, option, type):
        if not self.types.get(section):
            self.types[section] = {}

        self.types[section][option] = type

    def getType(self, section, option):
        tp = None
        try: tp = self.types[section][option]
        except: tp = 'unicode' if not tp else tp
        return tp

    def addOptions(self, section_name, options):
        # no additional actions (related to ro-rw options) are required here
        if not self.options.get(section_name):
            self.options[section_name] = options
        else:
            self.options[section_name] = mergeDicts(self.options[section_name], options)

    def getOptions(self):
        """Returns dict of UI-readable options

        To check, whether the option is readable self.isOptionReadable() is used
        """

        res = {}

        # it is required to filter invisible options for UI, but also we should
        # preserve original tree for server's purposes.
        # So, next loops do one thing: copy options to res and in the process
        #   1. omit NON-READABLE (for UI) options,  and
        #   2. put flags on READONLY options
        for section_key in self.options.keys():
            section_orig = self.options[section_key]
            section_name = section_orig.get('name') if 'name' in section_orig else section_key
            if self.isSectionReadable(section_name):
                section_copy = {}
                section_copy_groups = []
                for section_field in section_orig:
                    if section_field.lower() != 'groups':
                        section_copy[section_field] = section_orig[section_field]
                    else:
                        for group_orig in section_orig['groups']:
                            group_copy = {}
                            group_copy_options = []
                            for group_field in group_orig:
                                if group_field.lower() != 'options':
                                    group_copy[group_field] = group_orig[group_field]
                                else:
                                    for option in group_orig[group_field]:
                                        option_name = option.get('name')
                                        # You should keep in mind, that READONLY = !IS_WRITABLE
                                        # and IS_READABLE is a different thing
                                        if self.isOptionReadable(section_name, option_name):
                                            group_copy_options.append(option)
                                            if not self.isOptionWritable(section_name, option_name):
                                                option['readonly'] = True
                            if len(group_copy_options)>0:
                                group_copy['options'] = group_copy_options
                                section_copy_groups.append(group_copy)
                if len(section_copy_groups)>0:
                    section_copy['groups'] = section_copy_groups
                    res[section_key] = section_copy

        return res

    def view(self, **kwargs):
        return {
            'options': self.getOptions(),
            'values': self.getValues()
        }

    def saveView(self, **kwargs):

        section = kwargs.get('section')
        option = kwargs.get('name')
        value = kwargs.get('value')

        if not self.isOptionWritable(section, option):
            self.log.warning('Option "%s.%s" isn\'t writable', (section, option))
            return {
                'success' : False,
            }

        from couchpotato.environment import Env
        soft_chroot = Env.get('softchroot')

        if self.getType(section, option) == 'directory':
            value = soft_chroot.chroot2abs(value)

        if self.getType(section, option) == 'directories':
            import json
            value = json.loads(value)
            if not (value and isinstance(value, list)):
                value = []
            value = map(soft_chroot.chroot2abs, value)
            value = self.directories_delimiter.join(value)

        # See if a value handler is attached, use that as value
        new_value = fireEvent('setting.save.%s.%s' % (section, option), value, single = True)

        self.set(section, option, (new_value if new_value else value).encode('unicode_escape'))
        self.save()

        # After save (for re-interval etc)
        fireEvent('setting.save.%s.%s.after' % (section, option), single = True)
        fireEvent('setting.save.%s.*.after' % section, single = True)

        return {
            'success': True
        }

    def isSectionReadable(self, section):
        meta = 'section_hidden' + self.optionMetaSuffix()
        try:
            return not self.p.getboolean(section, meta)
        except: pass

        # by default - every section is readable:
        return True

    def isOptionReadable(self, section, option):
        meta = option + self.optionMetaSuffix()
        if self.p.has_option(section, meta):
            meta_v = self.p.get(section, meta).lower()
            return (meta_v == 'rw') or (meta_v == 'ro')

        # by default - all is writable:
        return True

    def optionReadableCheckAndWarn(self, section, option):
        x = self.isOptionReadable(section, option)
        if not x:
            self.log.warning('Option "%s.%s" isn\'t readable', (section, option))
        return x

    def isOptionWritable(self, section, option):
        meta = option + self.optionMetaSuffix()
        if self.p.has_option(section, meta):
            return self.p.get(section, meta).lower() == 'rw'

        # by default - all is writable:
        return True

    def optionMetaSuffix(self):
        return '_internal_meta'

    def isOptionMeta(self, section, option):
        """ A helper method for detecting internal-meta options in the ini-file

        For a meta options used following names:
        * section_hidden_internal_meta = (True | False) - for section visibility
        * <OPTION>_internal_meta = (ro|rw|hidden) - for section visibility

        """

        suffix = self.optionMetaSuffix()
        return option.endswith(suffix)

    def getProperty(self, identifier):
        from couchpotato import get_db

        db = get_db()
        prop = None
        try:
            propert = db.get('property', identifier, with_doc = True)
            prop = propert['doc']['value']
        except ValueError:
            propert = db.get('property', identifier)
            fireEvent('database.delete_corrupted', propert.get('_id'))
        except:
            self.log.debug('Property "%s" doesn\'t exist: %s', (identifier, traceback.format_exc(0)))

        return prop

    def setProperty(self, identifier, value = ''):
        from couchpotato import get_db

        db = get_db()

        try:
            p = db.get('property', identifier, with_doc = True)
            p['doc'].update({
                'identifier': identifier,
                'value': toUnicode(value),
            })
            db.update(p['doc'])
        except:
            db.insert({
                '_t': 'property',
                'identifier': identifier,
                'value': toUnicode(value),
            })


class PropertyIndex(HashIndex):
    _version = 1

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(PropertyIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'property':
            return md5(data['identifier']).hexdigest(), None
