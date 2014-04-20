#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: util.py    Assorted utilities used in tmdb_api
# Python Library
# Author: Raymond Wagner
#-----------------------

from copy import copy
from locales import get_locale
from tmdb_auth import get_session


class NameRepr(object):
    """Mixin for __repr__ methods using 'name' attribute."""
    def __repr__(self):
        return u"<{0.__class__.__name__} '{0.name}'>"\
                    .format(self).encode('utf-8')


class SearchRepr(object):
    """
    Mixin for __repr__ methods for classes with '_name' and
    '_request' attributes.
    """
    def __repr__(self):
        name = self._name if self._name else self._request._kwargs['query']
        return u"<Search Results: {0}>".format(name).encode('utf-8')


class Poller(object):
    """
    Wrapper for an optional callable to populate an Element derived
    class with raw data, or data from a Request.
    """
    def __init__(self, func, lookup, inst=None):
        self.func = func
        self.lookup = lookup
        self.inst = inst
        if func:
            # with function, this allows polling data from the API
            self.__doc__ = func.__doc__
            self.__name__ = func.__name__
            self.__module__ = func.__module__
        else:
            # without function, this is just a dummy poller used for applying
            # raw data to a new Element class with the lookup table
            self.__name__ = '_populate'

    def __get__(self, inst, owner):
        # normal decorator stuff
        # return self for a class
        # return instantiated copy of self for an object
        if inst is None:
            return self
        func = None
        if self.func:
            func = self.func.__get__(inst, owner)
        return self.__class__(func, self.lookup, inst)

    def __call__(self):
        # retrieve data from callable function, and apply
        if not callable(self.func):
            raise RuntimeError('Poller object called without a source function')
        req = self.func()
        if ('language' in req._kwargs) or ('country' in req._kwargs) \
                and self.inst._locale.fallthrough:
            # request specifies a locale filter, and fallthrough is enabled
            # run a first pass with specified filter
            if not self.apply(req.readJSON(), False):
                return
            # if first pass results in missed data, run a second pass to
            # fill in the gaps
            self.apply(req.new(language=None, country=None).readJSON())
            # re-apply the filtered first pass data over top the second
            # unfiltered set. this is to work around the issue that the
            # properties have no way of knowing when they should or 
            # should not overwrite existing data. the cache engine will
            # take care of the duplicate query
        self.apply(req.readJSON())

    def apply(self, data, set_nones=True):
        # apply data directly, bypassing callable function
        unfilled = False
        for k, v in self.lookup.items():
            if (k in data) and \
                    ((data[k] is not None) if callable(self.func) else True):
                # argument received data, populate it
                setattr(self.inst, v, data[k])
            elif v in self.inst._data:
                # argument did not receive data, but Element already contains
                # some value, so skip this
                continue
            elif set_nones:
                # argument did not receive data, so fill it with None
                # to indicate such and prevent a repeat scan
                setattr(self.inst, v, None)
            else:
                # argument does not need data, so ignore it allowing it to
                # trigger a later poll. this is intended for use when
                # initializing a class with raw data, or when performing a
                # first pass through when performing locale fall through
                unfilled = True
        return unfilled


class Data(object):
    """
    Basic response definition class
    This maps to a single key in a JSON dictionary received from the API
    """
    def __init__(self, field, initarg=None, handler=None, poller=None,
                 raw=True, default=u'', lang=None, passthrough={}):
        """
        This defines how the dictionary value is to be processed by the
        poller
            field   -- defines the dictionary key that filters what data
                       this uses
            initarg -- (optional) specifies that this field must be
                       supplied when creating a new instance of the Element
                       class this definition is mapped to. Takes an integer
                       for the order it should be used in the input
                       arguments
            handler -- (optional) callable used to process the received
                       value before being stored in the Element object.
            poller  -- (optional) callable to be used if data is requested
                       and this value has not yet been defined. the
                       callable should return a dictionary of data from a
                       JSON query. many definitions may share a single
                       poller, which will be and the data used to populate
                       all referenced definitions based off their defined
                       field
            raw     -- (optional) if the specified handler is an Element
                       class, the data will be passed into it using the
                       'raw' keyword attribute.  setting this to false
                       will force the data to instead be passed in as the
                       first argument
        """
        self.field = field
        self.initarg = initarg
        self.poller = poller
        self.raw = raw
        self.default = default
        self.sethandler(handler)
        self.passthrough = passthrough

    def __get__(self, inst, owner):
        if inst is None:
            return self
        if self.field not in inst._data:
            if self.poller is None:
                return None
            self.poller.__get__(inst, owner)()
        return inst._data[self.field]

    def __set__(self, inst, value):
        if (value is not None) and (value != ''):
            value = self.handler(value)
        else:
            value = self.default
        if isinstance(value, Element):
            value._locale = inst._locale
            value._session = inst._session

            for source, dest in self.passthrough:
                setattr(value, dest, getattr(inst, source))
        inst._data[self.field] = value

    def sethandler(self, handler):
        # ensure handler is always callable, even for passthrough data
        if handler is None:
            self.handler = lambda x: x
        elif isinstance(handler, ElementType) and self.raw:
            self.handler = lambda x: handler(raw=x)
        else:
            self.handler = lambda x: handler(x)


class Datapoint(Data):
    pass


class Datalist(Data):
    """
    Response definition class for list data
    This maps to a key in a JSON dictionary storing a list of data
    """
    def __init__(self, field, handler=None, poller=None, sort=None, raw=True, passthrough={}):
        """
        This defines how the dictionary value is to be processed by the
        poller
            field   -- defines the dictionary key that filters what data
                       this uses
            handler -- (optional) callable used to process the received
                       value before being stored in the Element object.
            poller  -- (optional) callable to be used if data is requested
                       and this value has not yet been defined. the
                       callable should return a dictionary of data from a
                       JSON query. many definitions may share a single
                       poller, which will be and the data used to populate
                       all referenced definitions based off their defined
                       field
            sort    -- (optional) name of attribute in resultant data to be
                       used to sort the list after processing. this
                       effectively requires a handler be defined to process
                       the data into something that has attributes
            raw     -- (optional) if the specified handler is an Element
                       class, the data will be passed into it using the
                       'raw' keyword attribute.  setting this to false will
                       force the data to instead be passed in as the first
                       argument
        """
        super(Datalist, self).__init__(field, None, handler, poller, raw, passthrough=passthrough)
        self.sort = sort

    def __set__(self, inst, value):
        data = []
        if value:
            for val in value:
                val = self.handler(val)
                if isinstance(val, Element):
                    val._locale = inst._locale
                    val._session = inst._session

                    for source, dest in self.passthrough.items():
                        setattr(val, dest, getattr(inst, source))

                data.append(val)
            if self.sort:
                if self.sort is True:
                    data.sort()
                else:
                    data.sort(key=lambda x: getattr(x, self.sort))
        inst._data[self.field] = data


class Datadict(Data):
    """
    Response definition class for dictionary data
    This maps to a key in a JSON dictionary storing a dictionary of data
    """
    def __init__(self, field, handler=None, poller=None, raw=True,
                       key=None, attr=None, passthrough={}):
        """
        This defines how the dictionary value is to be processed by the
        poller
            field   -- defines the dictionary key that filters what data
                       this uses
            handler -- (optional) callable used to process the received
                       value before being stored in the Element object.
            poller  -- (optional) callable to be used if data is requested
                       and this value has not yet been defined. the
                       callable should return a dictionary of data from a
                       JSON query. many definitions may share a single
                       poller, which will be and the data used to populate
                       all referenced definitions based off their defined
                       field
            key     -- (optional) name of key in resultant data to be used
                       as the key in the stored dictionary. if this is not
                       the field name from the source data is used instead
            attr    -- (optional) name of attribute in resultant data to be
                       used as the key in the stored dictionary. if this is
                       not the field name from the source data is used
                       instead
            raw     -- (optional) if the specified handler is an Element
                       class, the data will be passed into it using the
                       'raw' keyword attribute.  setting this to false will
                       force the data to instead be passed in as the first
                       argument
        """
        if key and attr:
            raise TypeError("`key` and `attr` cannot both be defined")
        super(Datadict, self).__init__(field, None, handler, poller, raw, passthrough=passthrough)
        if key:
            self.getkey = lambda x: x[key]
        elif attr:
            self.getkey = lambda x: getattr(x, attr)
        else:
            raise TypeError("Datadict requires `key` or `attr` be defined " +
                            "for populating the dictionary")

    def __set__(self, inst, value):
        data = {}
        if value:
            for val in value:
                val = self.handler(val)
                if isinstance(val, Element):
                    val._locale = inst._locale
                    val._session = inst._session

                    for source, dest in self.passthrough.items():
                        setattr(val, dest, getattr(inst, source))

                data[self.getkey(val)] = val
        inst._data[self.field] = data

class ElementType( type ):
    """
    MetaClass used to pre-process Element-derived classes and set up the
    Data definitions
    """
    def __new__(mcs, name, bases, attrs):
        # any Data or Poller object defined in parent classes must be cloned
        # and processed in this class to function properly
        # scan through available bases for all such definitions and insert
        # a copy into this class's attributes
        # run in reverse order so higher priority values overwrite lower ones
        data = {}
        pollers = {'_populate':None}

        for base in reversed(bases):
            if isinstance(base, mcs):
                for k, attr in base.__dict__.items():
                    if isinstance(attr, Data):
                        # extract copies of each defined Data element from
                        # parent classes
                        attr = copy(attr)
                        attr.poller = attr.poller.func
                        data[k] = attr
                    elif isinstance(attr, Poller):
                        # extract copies of each defined Poller function
                        # from parent classes
                        pollers[k] = attr.func
        for k, attr in attrs.items():
            if isinstance(attr, Data):
                data[k] = attr
        if '_populate' in attrs:
            pollers['_populate'] = attrs['_populate']

        # process all defined Data attribues, testing for use as an initial
        # argument, and building a list of what Pollers are used to populate
        # which Data points
        pollermap = dict([(k, []) for k in pollers])
        initargs = []
        for k, v in data.items():
            v.name = k
            if v.initarg:
                initargs.append(v)
            if v.poller:
                pn = v.poller.__name__
                if pn not in pollermap:
                    pollermap[pn] = []
                if pn not in pollers:
                    pollers[pn] = v.poller
                pollermap[pn].append(v)
            else:
                pollermap['_populate'].append(v)

        # wrap each used poller function with a Poller class, and push into
        # the new class attributes
        for k, v in pollermap.items():
            if len(v) == 0:
                continue
            lookup = dict([(attr.field, attr.name) for attr in v])
            poller = Poller(pollers[k], lookup)
            attrs[k] = poller
            # backfill wrapped Poller into each mapped Data object, and ensure
            # the data elements are defined for this new class
            for attr in v:
                attr.poller = poller
                attrs[attr.name] = attr

        # build sorted list of arguments used for intialization
        attrs['_InitArgs'] = tuple(
                [a.name for a in sorted(initargs, key=lambda x: x.initarg)])
        return type.__new__(mcs, name, bases, attrs)

    def __call__(cls, *args, **kwargs):
        obj = cls.__new__(cls)
        if ('locale' in kwargs) and (kwargs['locale'] is not None):
            obj._locale = kwargs['locale']
        else:
            obj._locale = get_locale()

        if 'session' in kwargs:
            obj._session = kwargs['session']
        else:
            obj._session = get_session()

        obj._data = {}
        if 'raw' in kwargs:
            # if 'raw' keyword is supplied, create populate object manually
            if len(args) != 0:
                raise TypeError(
                        '__init__() takes exactly 2 arguments (1 given)')
            obj._populate.apply(kwargs['raw'], False)
        else:
            # if not, the number of input arguments must exactly match that
            # defined by the Data definitions
            if len(args) != len(cls._InitArgs):
                raise TypeError(
                        '__init__() takes exactly {0} arguments ({1} given)'\
                            .format(len(cls._InitArgs)+1, len(args)+1))
            for a, v in zip(cls._InitArgs, args):
                setattr(obj, a, v)

        obj.__init__()
        return obj


class Element( object ):
    __metaclass__ = ElementType
    _lang = 'en'
