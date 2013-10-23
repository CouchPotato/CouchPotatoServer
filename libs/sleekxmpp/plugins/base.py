# -*- encoding: utf-8 -*-

"""
    sleekxmpp.plugins.base
    ~~~~~~~~~~~~~~~~~~~~~~

    This module provides XMPP functionality that
    is specific to client connections.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2012 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

import sys
import copy
import logging
import threading


if sys.version_info >= (3, 0):
    unicode = str


log = logging.getLogger(__name__)


#: Associate short string names of plugins with implementations. The
#: plugin names are based on the spec used by the plugin, such as
#: `'xep_0030'` for a plugin that implements XEP-0030.
PLUGIN_REGISTRY = {}

#: In order to do cascading plugin disabling, reverse dependencies
#: must be tracked.
PLUGIN_DEPENDENTS = {}

#: Only allow one thread to manipulate the plugin registry at a time.
REGISTRY_LOCK = threading.RLock()


class PluginNotFound(Exception):
    """Raised if an unknown plugin is accessed."""


def register_plugin(impl, name=None):
    """Add a new plugin implementation to the registry.

    :param class impl: The plugin class.

    The implementation class must provide a :attr:`~BasePlugin.name`
    value that will be used as a short name for enabling and disabling
    the plugin. The name should be based on the specification used by
    the plugin. For example, a plugin implementing XEP-0030 would be
    named `'xep_0030'`.
    """
    if name is None:
        name = impl.name
    with REGISTRY_LOCK:
        PLUGIN_REGISTRY[name] = impl
        if name not in PLUGIN_DEPENDENTS:
            PLUGIN_DEPENDENTS[name] = set()
        for dep in impl.dependencies:
            if dep not in PLUGIN_DEPENDENTS:
                PLUGIN_DEPENDENTS[dep] = set()
            PLUGIN_DEPENDENTS[dep].add(name)


def load_plugin(name, module=None):
    """Find and import a plugin module so that it can be registered.

    This function is called to import plugins that have selected for
    enabling, but no matching registered plugin has been found.

    :param str name: The name of the plugin. It is expected that
                     plugins are in packages matching their name,
                     even though the plugin class name does not
                     have to match.
    :param str module: The name of the base module to search
                       for the plugin.
    """
    try:
        if not module:
            try:
                module = 'sleekxmpp.plugins.%s' % name
                __import__(module)
                mod = sys.modules[module]
            except ImportError:
                module = 'sleekxmpp.features.%s' % name
                __import__(module)
                mod = sys.modules[module]
        elif isinstance(module, (str, unicode)):
            __import__(module)
            mod = sys.modules[module]
        else:
            mod = module

        # Add older style plugins to the registry.
        if hasattr(mod, name):
            plugin = getattr(mod, name)
            if hasattr(plugin, 'xep') or hasattr(plugin, 'rfc'):
                plugin.name = name
                # Mark the plugin as an older style plugin so
                # we can work around dependency issues.
                plugin.old_style = True
            register_plugin(plugin, name)
    except ImportError:
        log.exception("Unable to load plugin: %s", name)


class PluginManager(object):
    def __init__(self, xmpp, config=None):
        #: We will track all enabled plugins in a set so that we
        #: can enable plugins in batches and pull in dependencies
        #: without problems.
        self._enabled = set()

        #: Maintain references to active plugins.
        self._plugins = {}

        self._plugin_lock = threading.RLock()

        #: Globally set default plugin configuration. This will
        #: be used for plugins that are auto-enabled through
        #: dependency loading.
        self.config = config if config else {}

        self.xmpp = xmpp

    def register(self, plugin, enable=True):
        """Register a new plugin, and optionally enable it.

        :param class plugin: The implementation class of the plugin
                             to register.
        :param bool enable: If ``True``, immediately enable the
                            plugin after registration.
        """
        register_plugin(plugin)
        if enable:
            self.enable(plugin.name)

    def enable(self, name, config=None, enabled=None):
        """Enable a plugin, including any dependencies.

        :param string name: The short name of the plugin.
        :param dict config: Optional settings dictionary for
                            configuring plugin behaviour.
        """
        top_level = False
        if enabled is None:
            enabled = set()

        with self._plugin_lock:
            if name not in self._enabled:
                enabled.add(name)
                self._enabled.add(name)
                if not self.registered(name):
                    load_plugin(name)

                plugin_class = PLUGIN_REGISTRY.get(name, None)
                if not plugin_class:
                    raise PluginNotFound(name)

                if config is None:
                    config = self.config.get(name, None)

                plugin = plugin_class(self.xmpp, config)
                self._plugins[name] = plugin
                for dep in plugin.dependencies:
                    self.enable(dep, enabled=enabled)
                plugin._init()

        if top_level:
            for name in enabled:
                if hasattr(self.plugins[name], 'old_style'):
                    # Older style plugins require post_init()
                    # to run just before stream processing begins,
                    # so we don't call it here.
                    pass
                self.plugins[name].post_init()

    def enable_all(self, names=None, config=None):
        """Enable all registered plugins.

        :param list names: A list of plugin names to enable. If
                           none are provided, all registered plugins
                           will be enabled.
        :param dict config: A dictionary mapping plugin names to
                            configuration dictionaries, as used by
                            :meth:`~PluginManager.enable`.
        """
        names = names if names else PLUGIN_REGISTRY.keys()
        if config is None:
            config = {}
        for name in names:
            self.enable(name, config.get(name, {}))

    def enabled(self, name):
        """Check if a plugin has been enabled.

        :param string name: The name of the plugin to check.
        :return: boolean
        """
        return name in self._enabled

    def registered(self, name):
        """Check if a plugin has been registered.

        :param string name: The name of the plugin to check.
        :return: boolean
        """
        return name in PLUGIN_REGISTRY

    def disable(self, name, _disabled=None):
        """Disable a plugin, including any dependent upon it.

        :param string name: The name of the plugin to disable.
        :param set _disabled: Private set used to track the
                              disabled status of plugins during
                              the cascading process.
        """
        if _disabled is None:
            _disabled = set()
        with self._plugin_lock:
            if name not in _disabled and name in self._enabled:
                _disabled.add(name)
                plugin = self._plugins.get(name, None)
                if plugin is None:
                    raise PluginNotFound(name)
                for dep in PLUGIN_DEPENDENTS[name]:
                    self.disable(dep, _disabled)
                plugin._end()
                if name in self._enabled:
                    self._enabled.remove(name)
                del self._plugins[name]

    def __keys__(self):
        """Return the set of enabled plugins."""
        return self._plugins.keys()

    def __getitem__(self, name):
        """
        Allow plugins to be accessed through the manager as if
        it were a dictionary.
        """
        plugin = self._plugins.get(name, None)
        if plugin is None:
            raise PluginNotFound(name)
        return plugin

    def __iter__(self):
        """Return an iterator over the set of enabled plugins."""
        return self._plugins.__iter__()

    def __len__(self):
        """Return the number of enabled plugins."""
        return len(self._plugins)


class BasePlugin(object):

    #: A short name for the plugin based on the implemented specification.
    #: For example, a plugin for XEP-0030 would use `'xep_0030'`.
    name = ''

    #: A longer name for the plugin, describing its purpose. For example,
    #: a plugin for XEP-0030 would use `'Service Discovery'` as its
    #: description value.
    description = ''

    #: Some plugins may depend on others in order to function properly.
    #: Any plugin names included in :attr:`~BasePlugin.dependencies` will
    #: be initialized as needed if this plugin is enabled.
    dependencies = set()

    #: The basic, standard configuration for the plugin, which may
    #: be overridden when initializing the plugin. The configuration
    #: fields included here may be accessed directly as attributes of
    #: the plugin. For example, including the configuration field 'foo'
    #: would mean accessing `plugin.foo` returns the current value of
    #: `plugin.config['foo']`.
    default_config = {}

    def __init__(self, xmpp, config=None):
        self.xmpp = xmpp
        if self.xmpp:
            self.api = self.xmpp.api.wrap(self.name)

        #: A plugin's behaviour may be configurable, in which case those
        #: configuration settings will be provided as a dictionary.
        self.config = copy.copy(self.default_config)
        if config:
            self.config.update(config)

    def __getattr__(self, key):
        """Provide direct access to configuration fields.

        If the standard configuration includes the option `'foo'`, then
        accessing `self.foo` should be the same as `self.config['foo']`.
        """
        if key in self.default_config:
            return self.config.get(key, None)
        else:
            return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        """Provide direct assignment to configuration fields.

        If the standard configuration includes the option `'foo'`, then
        assigning to `self.foo` should be the same as assigning to
        `self.config['foo']`.
        """
        if key in self.default_config:
            self.config[key] = value
        else:
            super(BasePlugin, self).__setattr__(key, value)

    def _init(self):
        """Initialize plugin state, such as registering event handlers.

        Also sets up required event handlers.
        """
        if self.xmpp is not None:
            self.xmpp.add_event_handler('session_bind', self.session_bind)
            if self.xmpp.session_bind_event.is_set():
                self.session_bind(self.xmpp.boundjid.full)
        self.plugin_init()
        log.debug('Loaded Plugin: %s', self.description)

    def _end(self):
        """Cleanup plugin state, and prepare for plugin removal.

        Also removes required event handlers.
        """
        if self.xmpp is not None:
            self.xmpp.del_event_handler('session_bind', self.session_bind)
        self.plugin_end()
        log.debug('Disabled Plugin: %s' % self.description)

    def plugin_init(self):
        """Initialize plugin state, such as registering event handlers."""
        pass

    def plugin_end(self):
        """Cleanup plugin state, and prepare for plugin removal."""
        pass

    def session_bind(self, jid):
        """Initialize plugin state based on the bound JID."""
        pass

    def post_init(self):
        """Initialize any cross-plugin state.

        Only needed if the plugin has circular dependencies.
        """
        pass


base_plugin = BasePlugin
