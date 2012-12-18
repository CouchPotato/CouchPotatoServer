from couchpotato.core.helpers.encoding import toUnicode
from elixir.entity import Entity
from elixir.fields import Field
from elixir.options import options_defaults, using_options
from elixir.relationships import ManyToMany, OneToMany, ManyToOne
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


class Movie(Entity):
    """Movie Resource a movie could have multiple releases
    The files belonging to the movie object are global for the whole movie
    such as trailers, nfo, thumbnails"""

    last_edit = Field(Integer, default = lambda: int(time.time()))

    library = ManyToOne('Library', cascade = 'delete, delete-orphan', single_parent = True)
    status = ManyToOne('Status')
    profile = ManyToOne('Profile')
    releases = OneToMany('Release', cascade = 'all, delete-orphan')
    files = ManyToMany('File', cascade = 'all, delete-orphan', single_parent = True)


class Library(Entity):
    """"""

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
    default = Field(Boolean, index = True)

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

    identifier = Field(String(100), index = True)

    movie = ManyToOne('Movie')
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
    movies = OneToMany('Movie')


class Quality(Entity):
    """Quality name of a release, DVD, 720P, DVD-Rip etc"""
    using_options(order_by = 'order')

    identifier = Field(String(20), unique = True)
    label = Field(Unicode(20))
    order = Field(Integer, index = True)

    size_min = Field(Integer)
    size_max = Field(Integer)

    releases = OneToMany('Release')
    profile_types = OneToMany('ProfileType')


class Profile(Entity):
    """"""
    using_options(order_by = 'order')

    label = Field(Unicode(50))
    order = Field(Integer, index = True)
    core = Field(Boolean)
    hide = Field(Boolean)

    movie = OneToMany('Movie')
    types = OneToMany('ProfileType', cascade = 'all, delete-orphan')


class ProfileType(Entity):
    """"""
    using_options(order_by = 'order')

    order = Field(Integer, index = True)
    finish = Field(Boolean)
    wait_for = Field(Integer)

    quality = ManyToOne('Quality')
    profile = ManyToOne('Profile')


class File(Entity):
    """File that belongs to a release."""

    path = Field(Unicode(255), nullable = False, unique = True)
    part = Field(Integer, default = 1)
    available = Field(Boolean)

    type = ManyToOne('FileType')
    properties = OneToMany('FileProperty')

    history = OneToMany('RenameHistory')
    movie = ManyToMany('Movie')
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


class Folder(Entity):
    """Renamer destination folders."""

    path = Field(Unicode(255))
    label = Field(Unicode(255))


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
