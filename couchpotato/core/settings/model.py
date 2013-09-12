from UserDict import DictMixin
from collections import OrderedDict
from couchpotato.core.helpers.encoding import toUnicode
from elixir.entity import Entity
from elixir.fields import Field
from elixir.options import options_defaults, using_options
from elixir.relationships import ManyToMany, OneToMany, ManyToOne
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import Integer, Unicode, UnicodeText, Boolean, String, \
    TypeDecorator
import json
import time

options_defaults["shortnames"] = True

# We would like to be able to create this schema in a specific database at
# will, so we can test it easily.
# Make elixir not bind to any session to make this possible.
#
# http://elixir.ematia.de/trac/wiki/Recipes/MultipleDatabasesOneMetadata
__session__ = None

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class JsonType(TypeDecorator):
    impl = UnicodeText

    def process_bind_param(self, value, dialect):
        try:
            return toUnicode(json.dumps(value, cls = SetEncoder))
        except:
            try:
                return toUnicode(json.dumps(value, cls = SetEncoder, encoding = 'latin-1'))
            except:
                raise

    def process_result_value(self, value, dialect):
        return json.loads(value if value else '{}')

class MutableDict(Mutable, dict):

    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)
            return Mutable.coerce(key, value)
        else:
            return value

    def __delitem(self, key):
        dict.__delitem__(self, key)
        self.changed()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(self)

    def update(self, *args, **kwargs):
        super(MutableDict, self).update(*args, **kwargs)
        self.changed()

MutableDict.associate_with(JsonType)


class Media(Entity):
    """Media Resource could have multiple releases
    The files belonging to the media object are global for the whole media
    such as trailers, nfo, thumbnails"""

    type = Field(String(10), default = "movie", index = True)
    last_edit = Field(Integer, default = lambda: int(time.time()), index = True)

    library = ManyToOne('Library', cascade = 'delete, delete-orphan', single_parent = True)
    status = ManyToOne('Status')
    profile = ManyToOne('Profile')
    category = ManyToOne('Category')
    releases = OneToMany('Release', cascade = 'all, delete-orphan')
    files = ManyToMany('File', cascade = 'all, delete-orphan', single_parent = True)


class Library(Entity):
    """"""
    using_options(inheritance = 'multi')

    # For Movies, CPS uses three: omdbapi (no prio !?), tmdb (prio 2) and couchpotatoapi (prio 1)
    type = Field(String(10), default = "movie", index = True)
    primary_provider = Field(String(10), default = "imdb", index = True)
    year = Field(Integer)
    identifier = Field(String(40), index = True)

    plot = Field(UnicodeText)
    tagline = Field(UnicodeText(255))
    info = Field(JsonType)

    status = ManyToOne('Status')
    media = OneToMany('Media', cascade = 'all, delete-orphan')
    titles = OneToMany('LibraryTitle', cascade = 'all, delete-orphan')
    files = ManyToMany('File', cascade = 'all, delete-orphan', single_parent = True)

    parent = ManyToOne('Library')
    children = OneToMany('Library')


class ShowLibrary(Library, DictMixin):
    using_options(inheritance = 'multi')

    last_updated = Field(Integer, index = True)
    show_status = Field(String(10), index = True)

    # XXX: Maybe we should convert this to seconds?
    # airs_time u'21:00'
    airs_time = Field(Unicode, index = True)

    # airs_dayofweek = Field(Integer, index = True)
    #    u'Monday':    1,
    #    u'Tuesday':   2,
    #    u'Wednesday': 4,
    #    u'Thursday':  8,
    #    u'Friday':    16,
    #    u'Saturday':  32,
    #    u'Sunday':    64,
    #    u'Daily':     127,
    airs_dayofweek = Field(Integer, index = True)

    def getSeasons(self):
        data = OrderedDict()
        for c in self.children:
            data[c.season_number] = c
        return data

    def getEpisodes(self, season_number):
        data = OrderedDict()
        for c in self.children[season_number].children:
            data[c.episode_number] = c
        return data

    # Read access to season by number: library[1] for season 1
    data = {}
    def __getitem__(self, key):
        if not self.data:
            self.setData()
        if key in self.data:
            return self.data[key]
        if hasattr(self.__class__, "__missing__"):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)
    def get(self, key, failobj = None):
        if key not in self:
            return failobj
        return self[key]
    def keys(self): return self.data.keys()
    def setData(self):
        for c in self.children:
            self.data[c.season_number] = c


class SeasonLibrary(Library, DictMixin):
    using_options(inheritance = 'multi')

    season_number = Field(Integer, index = True)
    last_updated = Field(Integer, index = True)

    def getEpisodes(self):
        data = OrderedDict()
        for c in self.children:
            data[c.episode_number] = c
        return data

    # Read access episode by number: library[1][4] for season 1, episode 4
    data = {}
    def __getitem__(self, key):
        if not self.data:
            self.setData()
        if key in self.data:
            return self.data[key]
        if hasattr(self.__class__, "__missing__"):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)
    def get(self, key, failobj = None):
        if key not in self:
            return failobj
        return self[key]
    def keys(self): return self.data.keys()
    def setData(self):
        for c in self.children:
            self.data[c.episode_number] = c


class EpisodeLibrary(Library):
    using_options(inheritance = 'multi')

    last_updated = Field(Integer, index = True)
    season_number = Field(Integer, index = True)
    episode_number = Field(Integer, index = True)


class LibraryTitle(Entity):
    """"""
    using_options(order_by = '-default')

    title = Field(Unicode)
    simple_title = Field(Unicode, index = True)
    default = Field(Boolean, default = False, index = True)

    language = OneToMany('Language')
    libraries = ManyToOne('Library')


class Language(Entity):
    """"""

    identifier = Field(String(20), index = True)
    label = Field(Unicode)

    titles = ManyToOne('LibraryTitle')


class Release(Entity):
    """Logically groups all files that belong to a certain release, such as
    parts of a movie, subtitles."""

    last_edit = Field(Integer, default = lambda: int(time.time()), index = True)
    identifier = Field(String(100), index = True)

    media = ManyToOne('Media')
    status = ManyToOne('Status')
    quality = ManyToOne('Quality')
    files = ManyToMany('File')
    info = OneToMany('ReleaseInfo', cascade = 'all, delete-orphan')

    def to_dict(self, deep = None, exclude = None):
        if not exclude: exclude = []
        if not deep: deep = {}

        orig_dict = super(Release, self).to_dict(deep = deep, exclude = exclude)

        new_info = {}
        for info in orig_dict.get('info', []):

            value = info['value']
            try: value = int(info['value'])
            except: pass

            new_info[info['identifier']] = value

        orig_dict['info'] = new_info

        return orig_dict


class ReleaseInfo(Entity):
    """Properties that can be bound to a file for off-line usage"""

    identifier = Field(String(50), index = True)
    value = Field(Unicode(255), nullable = False)

    release = ManyToOne('Release')


class Status(Entity):
    """The status of a release, such as Downloaded, Deleted, Wanted etc"""

    identifier = Field(String(20), unique = True)
    label = Field(Unicode(20))

    releases = OneToMany('Release')


class Quality(Entity):
    """Quality name of a release, DVD, 720p, DVD-Rip etc"""
    using_options(order_by = 'order')

    identifier = Field(String(20), unique = True)
    label = Field(Unicode(20))
    order = Field(Integer, default = 0, index = True)

    size_min = Field(Integer)
    size_max = Field(Integer)

    releases = OneToMany('Release')
    profile_types = OneToMany('ProfileType')


class Profile(Entity):
    """"""
    using_options(order_by = 'order')

    label = Field(Unicode(50))
    order = Field(Integer, default = 0, index = True)
    core = Field(Boolean, default = False)
    hide = Field(Boolean, default = False)

    media = OneToMany('Media')
    types = OneToMany('ProfileType', cascade = 'all, delete-orphan')

    def to_dict(self, deep = None, exclude = None):
        if not exclude: exclude = []
        if not deep: deep = {}

        orig_dict = super(Profile, self).to_dict(deep = deep, exclude = exclude)
        orig_dict['core'] = orig_dict.get('core') or False
        orig_dict['hide'] = orig_dict.get('hide') or False

        return orig_dict

class Category(Entity):
    """"""
    using_options(order_by = 'order')

    label = Field(Unicode(50))
    order = Field(Integer, default = 0, index = True)
    required = Field(Unicode(255))
    preferred = Field(Unicode(255))
    ignored = Field(Unicode(255))
    destination = Field(Unicode(255))

    media = OneToMany('Media')
    destination = Field(Unicode(255))


class ProfileType(Entity):
    """"""
    using_options(order_by = 'order')

    order = Field(Integer, default = 0, index = True)
    finish = Field(Boolean, default = True)
    wait_for = Field(Integer, default = 0)

    quality = ManyToOne('Quality')
    profile = ManyToOne('Profile')


class File(Entity):
    """File that belongs to a release."""

    path = Field(Unicode(255), nullable = False, unique = True)
    part = Field(Integer, default = 1)
    available = Field(Boolean, default = True)

    type = ManyToOne('FileType')
    properties = OneToMany('FileProperty')

    history = OneToMany('RenameHistory')
    media = ManyToMany('Media')
    release = ManyToMany('Release')
    library = ManyToMany('Library')


class FileType(Entity):
    """Types could be trailer, subtitle, movie, partial movie etc."""

    identifier = Field(String(20), unique = True)
    type = Field(Unicode(20))
    name = Field(Unicode(50), nullable = False)

    files = OneToMany('File')


class FileProperty(Entity):
    """Properties that can be bound to a file for off-line usage"""

    identifier = Field(String(20), index = True)
    value = Field(Unicode(255), nullable = False)

    file = ManyToOne('File')


class RenameHistory(Entity):
    """Remembers from where to where files have been moved."""

    old = Field(Unicode(255))
    new = Field(Unicode(255))

    file = ManyToOne('File')


class Notification(Entity):
    using_options(order_by = 'added')

    added = Field(Integer, default = lambda: int(time.time()))
    read = Field(Boolean, default = False)
    message = Field(Unicode(255))
    data = Field(JsonType)


class Properties(Entity):

    identifier = Field(String(50), index = True)
    value = Field(Unicode(255), nullable = False)


def setup():
    """Setup the database and create the tables that don't exists yet"""
    from elixir import setup_all, create_all
    from couchpotato.environment import Env

    engine = Env.getEngine()

    setup_all()
    create_all(engine)

    try:
        engine.execute("PRAGMA journal_mode = WAL")
        engine.execute("PRAGMA temp_store = MEMORY")
    except:
        pass
