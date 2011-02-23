from elixir.entity import Entity
from elixir.fields import Field
from elixir.options import options_defaults
from elixir.relationships import OneToMany, ManyToOne
from sqlalchemy.types import Integer, String, Unicode

options_defaults["shortnames"] = True

# We would like to be able to create this schema in a specific database at
# will, so we can test it easily.
# Make elixir not bind to any session to make this possible.
#
# http://elixir.ematia.de/trac/wiki/Recipes/MultipleDatabasesOneMetadata
__session__ = None

class Resource(Entity):
    """Represents a resource of movies.  
    This resources can be online or offline."""
    name = Field(Unicode(255))
    path = Field(Unicode(255))
    releases = OneToMany('Release')


class Release(Entity):
    """Logically groups all files that belong to a certain release, such as
    parts of a movie, subtitles, nfo, trailers etc."""
    files = OneToMany('File')
    mooli_id = Field(Integer)
    resource = ManyToOne('Resource')


class File(Entity):
    """File that belongs to a release."""
    history = OneToMany('RenameHistory')
    path = Field(Unicode(255), nullable = False, unique = True)
    # Subtitles can have multiple parts, too
    part = Field(Integer)
    release = ManyToOne('Release')
    # Let's remember the size so we know about offline media.
    size = Field(Integer, nullable = False)
    type = ManyToOne('FileType')


class FileType(Entity):
    """Types could be trailer, subtitle, movie, partial movie etc."""
    identifier = Field(String(20), unique = True)
    name = Field(Unicode(255), nullable = False)
    files = OneToMany('File')


class RenameHistory(Entity):
    """Remembers from where to where files have been moved."""
    file = ManyToOne('File')
    old = Field(String(255))
    new = Field(String(255))
