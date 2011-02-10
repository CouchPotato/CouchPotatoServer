from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.schema import ThreadLocalMetaData
from elixir import *

# We would like to be able to create this schema in a specific database at
# will, so we can test it easily.
# Make elixir not bind to any session to make this possible.
#
# http://elixir.ematia.de/trac/wiki/Recipes/MultipleDatabasesOneMetadata
__session__ = None


class Resource(Entity):
    """Represents a resource of movies.  This recources can be online or
    offline."""
    name = Field(UnicodeString(255))
    path = Field(UnicodeString(255))
    releases = OneToMany('Release')


class Release(Entity):
    """Logically groups all files that belong to a certain release, such as
    parts of a movie, subtitles, nfo, trailers etc."""
    files = OneToMany('File')
    mooli_id = Field(Integer)
    resource = ManyToOne('Resource')


class File(Entity):
    """File that belongs to a release."""
    path = Field(UnicodeString(255))
    release = ManyToOne('Release')
    # Let's remember the size so we know about offline media.
    size = Field(Integer)
    type = ManyToOne('FileType')


class FileType(Entity):
    """Types could be trailer, subtitle, movie, partial movie etc."""
    name = Field(UnicodeString(255))
    files = OneToMany('File')
