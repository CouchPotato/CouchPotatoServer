from couchpotato.core.helpers.encoding import toUnicode
from elixir.entity import Entity
from elixir.fields import Field
from elixir.options import options_defaults, using_options
from elixir.relationships import ManyToMany, OneToMany, ManyToOne
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import Integer, Unicode, UnicodeText, Boolean, String, \
    TypeDecorator, Float, BLOB
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

class Movie(Entity):
    """Movie Resource a movie could have multiple releases
    The files belonging to the movie object are global for the whole movie
    such as trailers, nfo, thumbnails"""

    type = Field(String(10), default="movie", index=True)
    last_edit = Field(Integer, default = lambda: int(time.time()), index = True)

    library = ManyToOne('Library', cascade = 'delete, delete-orphan', single_parent = True)
    status = ManyToOne('Status')
    profile = ManyToOne('Profile')
    category = ManyToOne('Category')
    releases = OneToMany('Release', cascade = 'all, delete-orphan')
    files = ManyToMany('File', cascade = 'all, delete-orphan', single_parent = True)


class Library(Entity):
    """"""

    # For Movies, CPS uses three: omdbapi (no prio !?), tmdb (prio 2) and couchpotatoapi (prio 1)
    provider = Field(String(10), default="imdb", index=True)
    year = Field(Integer)
    identifier = Field(String(20), index = True)

    plot = Field(UnicodeText)
    tagline = Field(UnicodeText(255))
    info = Field(JsonType)

    status = ManyToOne('Status')
    movies = OneToMany('Movie', cascade = 'all, delete-orphan')
    titles = OneToMany('LibraryTitle', cascade = 'all, delete-orphan')
    files = ManyToMany('File', cascade = 'all, delete-orphan', single_parent = True)


class LibraryTitle(Entity):
    """"""
    using_options(order_by = '-default')

    title = Field(Unicode)
    simple_title = Field(Unicode, index = True)
    default = Field(Boolean, default = False, index = True)

    language = OneToMany('Language')
    libraries = ManyToOne('Library')

    
#class Show(Entity):
    #"""Combined Show and Library"""
    
    #using_options(order_by = '-default')        # ???
    
    #last_edit = Field(Integer, default = lambda: int(time.time()), index = True)
    ##identifier = Field(String(20), index = True)
    
    #title = Field(Unicode)                      # Show title
    #simple_title = Field(Unicode, index = True) # Simple show title
    #default = Field(Boolean, default = False, index = True)  # ???

    ### Wont need the following commented out vars since a show can not be downloaded,
    ### only episodes can be
    ###status = ManyToOne('Status')                # Download, watched, etc
    ###releases = OneToMany('Release', cascade = 'all, delete-orphan')  # List all available releases that can be downloaded?
    ###files = ManyToMany('File', cascade = 'all, delete-orphan', single_parent = True)  # File on hard drive
    #profile = ManyToOne('Profile')              # ??? Quality ???
    #category = ManyToOne('Category')            # ???
    #language = OneToMany('Language')            # Language ??? (en) ???
    
    ## New fields
    #air_by_date = Field(Boolean, default=False) # True if no season or episode number
    #original_air_date = Field(Integer)          # First date ever released
    #year = Field(Integer)                       # 1983
    #air_day = Field(Integer)                    # Monday, Tuesday...
    #air_time = Field(Integer)                   # 8PM EST
    #series_id = Field(Integer)                  # Series id
    #show_stauts = Field(Integer)                # Continuing, Ended
    
    #duration = Field(Integer)                   # Length of show in seconds
    #summary = Field(Unicode)                    # Description of show
    #network = Field(Unicode)                    # ABC, Fox
    #rating = Field(Float)                       # 0.000-10.000 (star rating) 
    #content_rating = Field(Unicode)             # "TV-PG"
    
    #default_provider = Field(Integer, default=0)# thetvdb for example; allows per show providers
    
    #genre = ManyToMany('Genre')                 # Genre (comedy, etc)
    #episodes = OneToMany('Episode')             # All the episodes that belong to this show
    #seasons = ManyToOne('Season')               # Seasons artwork
    #banners = ManyToOne('Banner')               # Banner artwork
    #posters = ManyToOne('Poster')               # Poster artwork
    #fanart = ManyToOne('Fanart')                # Fanart artwork
    #actors = ManyToMany('Actor')                # Actor info and artwork
    #provider_ids = ManyToMany('ProviderIds')    # 'imdb_id',  'zap2it_id', 'tvrage'
    #titles = OneToMany('ShowTitle', cascade = 'all, delete-orphan')
    
    
#class ShowTitle(Entity):
    #""""""
    #using_options(order_by = '-default')

    #title = Field(Unicode)
    #simple_title = Field(Unicode, index = True)
    #default = Field(Boolean, default = False, index = True)

    #language = OneToMany('Language')
    #shows = ManyToOne('Show')
    
    
#class Episode(Entity):
    #"""Combined Show and Library"""
    
    ##using_options(order_by = '-default')        # ???
    ##identifier = Field(String(20), index = True)
    
    #last_edit = Field(Integer, default = lambda: int(time.time()), index = True)
    #title = Field(Unicode)                      # Show title
    #simple_title = Field(Unicode, index = True) # Simple show title
    #default = Field(Boolean, default = False, index = True)  # ???

    #status = ManyToOne('Status')                # Download, watched, etc
    #profile = ManyToOne('Profile')              # ??? Quality ???
    #category = ManyToOne('Category')            # ???
    #releases = OneToMany('Release', cascade = 'all, delete-orphan')  # List all available releases that can be downloaded?
    #files = ManyToMany('File', cascade = 'all, delete-orphan', single_parent = True)  # File on hard drive
    #language = OneToMany('Language')            # Language ??? (en) ???
    
    ## New fields
    #season = Field(Integer)                     # Season number
    #number = Field(Integer)                     # Episode number
    #image = Field(BLOB)                         # Episode Image (XXX: What to do with images?)
    #air_date = Field(Integer)                   # Origianl air date
    #duration = Field(Integer)                   # Length of show (24:34) in seconds
    #summary = Field(Unicode)                    # Description of show
    #rating = Field(Float)                       # 0.000-10.000 (star rating) 
    #content_rating = Field(Unicode)             # "TV-PG"
    #production_code = Field(Unicode)          # Production code (should this be an Integer)
    
    #show = ManyToOne('Show')                    # Parent show
    #actors = ManyToMany('Actor')                # Guest Actor info and artwork
    #directors = ManyToMany('Director')          # Directors of episode
    #writers = ManyToMany('Writer')              # Writers of episode
    #provider_ids = ManyToMany('ProviderIds')    # 'imdb_id',  'zap2it_id', 'tvrage'
    
    
#class Fanart(Entity):
    #"""Stub for Now"""
    #show = OneToMany('Show')
    
#class Actor(Entity):
    #"""Stub for Now"""
    #shows = ManyToMany('Show')
    #episodes = ManyToMany('Episode')
    
#class Director(Entity):
    #"""Stub for Now"""
    #episodes = ManyToMany('Episode')
    
#class Writer(Entity):
    #"""Stub for Now"""
    #episodes = ManyToMany('Episode')
    
#class Genre(Entity):
    #"""Stub for Now"""
    #shows = ManyToMany('Show')
    
#class Season(Entity):
    #"""Stub for Now"""
    #show = OneToMany('Show')
    
#class Banner(Entity):
    #"""Stub for Now"""
    #show = OneToMany('Show')
    
#class Poster(Entity):
    #"""Stub for Now"""
    #show = OneToMany('Show')
    
#class ProviderIds(Entity):
    #"""Stub for Now"""
    #shows = ManyToMany('Show')
    #episodes = ManyToMany('Episode')
    
    
class Language(Entity):
    """"""

    identifier = Field(String(20), index = True)
    label = Field(Unicode)

    titles = ManyToOne('LibraryTitle')
    #show_titles = ManyToOne('ShowTitle')
    #show = ManyToOne('Show')
    #episode = ManyToOne('Episode')


class Release(Entity):
    """Logically groups all files that belong to a certain release, such as
    parts of a movie, subtitles."""

    last_edit = Field(Integer, default = lambda: int(time.time()), index = True)
    identifier = Field(String(100), index = True)

    movie = ManyToOne('Movie')
    #episode = ManyToOne('Episode')
    status = ManyToOne('Status')
    quality = ManyToOne('Quality')
    files = ManyToMany('File')
    info = OneToMany('ReleaseInfo', cascade = 'all, delete-orphan')

    def to_dict(self, deep = {}, exclude = []):
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
    #movies = OneToMany('Movie')
    #episodes = OneToMany('Episode')


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

    movie = OneToMany('Movie')
    #show = OneToMany('Show')
    #episode = OneToMany('Episode')
    types = OneToMany('ProfileType', cascade = 'all, delete-orphan')

    def to_dict(self, deep = {}, exclude = []):
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

    movie = OneToMany('Movie')
    #show = OneToMany('Show')
    #episode = OneToMany('Episode')
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
    movie = ManyToMany('Movie')
    #episodes = ManyToMany('Episode')
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
