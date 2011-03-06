from elixir.entity import Entity
from elixir.fields import Field
from elixir.options import options_defaults
from elixir.relationships import OneToMany, ManyToOne
from sqlalchemy.types import Integer, String, Unicode, UnicodeText, Boolean

options_defaults["shortnames"] = True

# We would like to be able to create this schema in a specific database at
# will, so we can test it easily.
# Make elixir not bind to any session to make this possible.
#
# http://elixir.ematia.de/trac/wiki/Recipes/MultipleDatabasesOneMetadata
__session__ = None


class Movie(Entity):
    """Movie Resource a movie could have multiple releases
    The files belonging to the movie object are global for the whole movie
    such as trailers, nfo, thumbnails"""

    mooli_id = Field(Integer)

    profile = ManyToOne('Profile')
    releases = OneToMany('Release')
    files = OneToMany('File')


class Release(Entity):
    """Logically groups all files that belong to a certain release, such as
    parts of a movie, subtitles."""

    movie = ManyToOne('Movie')
    status = ManyToOne('Status')
    quality = ManyToOne('Quality')
    files = OneToMany('File')
    history = OneToMany('History')


class Status(Entity):
    """The status of a release, such as Downloaded, Deleted, Wanted etc"""

    identifier = Field(String(20), unique = True)
    label = Field(String(20))

    releases = OneToMany('Release')


class Quality(Entity):
    """Quality name of a release, DVD, 720P, DVD-Rip etc"""

    identifier = Field(String(20), unique = True)
    label = Field(String(20))

    releases = OneToMany('Release')
    profile_types = ManyToOne('ProfileType')

class Profile(Entity):
    """"""

    identifier = Field(String(20), unique = True)
    label = Field(Unicode(50))
    order = Field(Integer)
    wait_for = Field(Integer)

    movie = OneToMany('Movie')
    profile_type = OneToMany('ProfileType')

class ProfileType(Entity):
    """"""

    order = Field(Integer)
    mark_completed = Field(Boolean)
    wait_for = Field(Integer)

    type = OneToMany('Quality')
    profile = ManyToOne('Profile')

class File(Entity):
    """File that belongs to a release."""

    path = Field(Unicode(255), nullable = False, unique = True)
    part = Field(Integer)

    history = OneToMany('RenameHistory')
    movie = ManyToOne('Movie')
    release = ManyToOne('Release')
    type = ManyToOne('FileType')
    properties = OneToMany('FileProperty')


class FileType(Entity):
    """Types could be trailer, subtitle, movie, partial movie etc."""

    identifier = Field(String(20), unique = True)
    name = Field(Unicode(50), nullable = False)

    files = OneToMany('File')


class FileProperty(Entity):
    """Properties that can be bound to a file for off-line usage"""

    identifier = Field(String(20))
    value = Field(Unicode(255), nullable = False)

    file = ManyToOne('File')


class History(Entity):
    """History of actions that are connected to a certain release,
    such as, renamed to, downloaded, deleted, download subtitles etc"""

    message = Field(UnicodeText())
    release = ManyToOne('Release')

class RenameHistory(Entity):
    """Remembers from where to where files have been moved."""

    old = Field(String(255))
    new = Field(String(255))

    file = ManyToOne('File')


def setup():
    """ Setup the database and create the tables that don't exists yet """
    from elixir import setup_all, create_all
    from couchpotato import get_engine

    setup_all()
    create_all(get_engine())
