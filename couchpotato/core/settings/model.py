import uuid
import datetime

from sqlalchemy import Column, ForeignKey, Table, Index
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, object_mapper, ColumnProperty, class_mapper
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.orm.query import Query
from sqlalchemy.ext.declarative import declarative_base
from couchpotato.core.helpers.encoding import toUnicode
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import Integer, Unicode, UnicodeText, Boolean, String, \
    TypeDecorator
import json
import time


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

Base = declarative_base()

COLUMN_BLACKLIST = ('_sa_polymorphic_on', )

def is_mapped_class(cls):
    try:
        class_mapper(cls)
        return True
    except:
        return False

def is_like_list(instance, relation):
    """Returns ``True`` if and only if the relation of `instance` whose name is
`relation` is list-like.

A relation may be like a list if, for example, it is a non-lazy one-to-many
relation, or it is a dynamically loaded one-to-many.

"""
    if relation in instance._sa_class_manager:
        return instance._sa_class_manager[relation].property.uselist
    related_value = getattr(type(instance), relation, None)
    return isinstance(related_value, AssociationProxy)

class TableHelper():
    def to_dict(self, deep = None, exclude = None, include = None,
                exclude_relations = None, include_relations = None,
                include_methods = None):
        instance = self

        if (exclude is not None or exclude_relations is not None) and \
                (include is not None or include_relations is not None):
            raise ValueError('Cannot specify both include and exclude.')
        # create a list of names of columns, including hybrid properties
        try:
            columns = [p.key for p in object_mapper(instance).iterate_properties
                       if isinstance(p, ColumnProperty)]
        except UnmappedInstanceError:
            return instance
        for parent in type(instance).mro():
            columns += [key for key, value in parent.__dict__.items()
                        if isinstance(value, hybrid_property)]
        # filter the columns based on exclude and include values
        if exclude is not None:
            columns = (c for c in columns if c not in exclude)
        elif include is not None:
            columns = (c for c in columns if c in include)
        # create a dictionary mapping column name to value
        result = dict((col, getattr(instance, col)) for col in columns
                      if not (col.startswith('__') or col in COLUMN_BLACKLIST))
        # add any included methods
        if include_methods is not None:
            result.update(dict((method, getattr(instance, method)()) for method in include_methods if not '.' in method))
        # Check for objects in the dictionary that may not be serializable by
        # default. Specifically, convert datetime and date objects to ISO 8601
        # format, and convert UUID objects to hexadecimal strings.
        for key, value in result.items():
            # TODO We can get rid of this when issue #33 is resolved.
            if isinstance(value, datetime.date):
                result[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif is_mapped_class(type(value)):
                result[key] = value.to_dict()
        # recursively call _to_dict on each of the `deep` relations
        deep = deep or {}
        for relation, rdeep in deep.items():
            # Get the related value so we can see if it is None, a list, a query
            # (as specified by a dynamic relationship loader), or an actual
            # instance of a model.
            relatedvalue = getattr(instance, relation)
            if relatedvalue is None:
                result[relation] = None
                continue
            # Determine the included and excluded fields for the related model.
            newexclude = None
            newinclude = None
            if exclude_relations is not None and relation in exclude_relations:
                newexclude = exclude_relations[relation]
            elif (include_relations is not None and
                          relation in include_relations):
                newinclude = include_relations[relation]
            # Determine the included methods for the related model.
            newmethods = None
            if include_methods is not None:
                newmethods = [method.split('.', 1)[1] for method in include_methods
                              if method.split('.', 1)[0] == relation]
            if is_like_list(instance, relation):
                result[relation] = [inst.to_dict(rdeep, exclude = newexclude,
                                                 include = newinclude,
                                                 include_methods = newmethods)
                                    for inst in relatedvalue]
                continue
            # If the related value is dynamically loaded, resolve the query to get
            # the single instance.
            if isinstance(relatedvalue, Query):
                relatedvalue = relatedvalue.one()
            result[relation] = relatedvalue.to_dict(rdeep, exclude = newexclude,
                                                    include = newinclude,
                                                    include_methods = newmethods)

        return result


movie_files = Table('movie_files__file_movie', Base.metadata,
    Column('movie_id', Integer, ForeignKey('movie.id'), nullable = False),
    Column('file_id', Integer, ForeignKey('file.id'), nullable = False),
    Index('movie_files_idx', 'movie_id', 'file_id', unique = True)
)

release_files = Table('release_files__file_release', Base.metadata,
    Column('release_id', Integer, ForeignKey('release.id'), nullable = False),
    Column('file_id', Integer, ForeignKey('file.id'), nullable = False),
    Index('release_files_idx', 'release_id', 'file_id', unique = True)
)

library_files = Table('library_files__file_library', Base.metadata,
    Column('library_id', Integer, ForeignKey('library.id'), nullable = False),
    Column('file_id', Integer, ForeignKey('file.id'), nullable = False),
    Index('library_files_idx', 'library_id', 'file_id', unique = True)
)

class Movie(Base, TableHelper):
    __tablename__ = 'movie'
    id = Column(Integer, primary_key = True)

    """Movie Resource a movie could have multiple releases
    The files belonging to the movie object are global for the whole movie
    such as trailers, nfo, thumbnails"""

    last_edit = Column(Integer, default = lambda: int(time.time()), index = True)
    type = 'movie'  # Compat tv branch

    library_id = Column(Integer, ForeignKey('library.id'), index = True)
    status_id = Column(Integer, ForeignKey('status.id'), index = True)
    profile_id = Column(Integer, ForeignKey('profile.id'), index = True)
    category_id = Column(Integer, ForeignKey('category.id'), index = True)

    library = relationship('Library') #cascade = 'delete, delete-orphan', single_parent = True)
    status = relationship('Status')
    profile = relationship('Profile')
    category = relationship('Category')
    releases = relationship('Release') #, cascade = 'all, delete-orphan')
    files = relationship('File', secondary = movie_files) #, cascade = 'all, delete-orphan', single_parent = True)

Media = Movie  # Compat tv branch


class Library(Base, TableHelper):
    __tablename__ = 'library'
    id = Column(Integer, primary_key = True)

    """"""

    year = Column(Integer)
    identifier = Column(String(20), index = True)

    plot = Column(UnicodeText)
    tagline = Column(UnicodeText(255))
    info = Column(JsonType)

    status_id = Column(Integer, ForeignKey('status.id'), index = True)
    status = relationship('Status')

    movies = relationship('Movie') #, cascade = 'all, delete-orphan')
    titles = relationship('LibraryTitle', order_by="desc(LibraryTitle.default)") #, cascade = 'all, delete-orphan')
    files = relationship('File', secondary = library_files) #, cascade = 'all, delete-orphan', single_parent = True)


class LibraryTitle(Base, TableHelper):
    __tablename__ = 'librarytitle'
    id = Column(Integer, primary_key = True)

    """"""

    #using_options(order_by = '-default')

    title = Column(Unicode)
    simple_title = Column(Unicode, index = True)
    default = Column(Boolean, default = False, index = True)

    language = relationship('Language')

    libraries_id = Column(Integer, ForeignKey('library.id'), index = True)
    libraries = relationship('Library')


class Language(Base, TableHelper):
    __tablename__ = 'language'
    id = Column(Integer, primary_key = True)

    """"""

    identifier = Column(String(20), index = True)
    label = Column(Unicode)

    titles_id = Column(Integer, ForeignKey('librarytitle.id'), index = True)
    titles = relationship('LibraryTitle')


class Release(Base, TableHelper):
    __tablename__ = 'release'
    id = Column(Integer, primary_key = True)

    """Logically groups all files that belong to a certain release, such as
    parts of a movie, subtitles."""

    last_edit = Column(Integer, default = lambda: int(time.time()), index = True)
    identifier = Column(String(100), index = True)

    movie_id = Column(Integer, ForeignKey('movie.id'), index = True)
    movie = relationship('Movie')

    status_id = Column(Integer, ForeignKey('status.id'), index = True)
    status = relationship('Status')

    quality_id = Column(Integer, ForeignKey('quality.id'), index = True)
    quality = relationship('Quality')

    files = relationship('File', secondary = release_files)
    info = relationship('ReleaseInfo') #, cascade = 'all, delete-orphan')

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


class ReleaseInfo(Base, TableHelper):
    __tablename__ = 'releaseinfo'
    id = Column(Integer, primary_key = True)

    """Properties that can be bound to a file for off-line usage"""

    identifier = Column(String(50), index = True)
    value = Column(Unicode(255), nullable = False)

    release_id = Column(Integer, ForeignKey('release.id'), index = True)
    release = relationship('Release')


class Status(Base, TableHelper):
    __tablename__ = 'status'
    id = Column(Integer, primary_key = True)

    """The status of a release, such as Downloaded, Deleted, Wanted etc"""

    identifier = Column(String(20), unique = True)
    label = Column(Unicode(20))

    releases = relationship('Release')
    movies = relationship('Movie')


class Quality(Base, TableHelper):
    __tablename__ = 'quality'
    id = Column(Integer, primary_key = True)

    """Quality name of a release, DVD, 720p, DVD-Rip etc"""

    #using_options(order_by = 'order')

    identifier = Column(String(20), unique = True)
    label = Column(Unicode(20))
    order = Column(Integer, default = 0, index = True)

    size_min = Column(Integer)
    size_max = Column(Integer)

    releases = relationship('Release')
    profile_types = relationship('ProfileType', order_by="asc(ProfileType.order)")


class Profile(Base, TableHelper):
    __tablename__ = 'profile'
    id = Column(Integer, primary_key = True)

    """"""

    #using_options(order_by = 'order')

    label = Column(Unicode(50))
    order = Column(Integer, default = 0, index = True)
    core = Column(Boolean, default = False)
    hide = Column(Boolean, default = False)

    movie = relationship('Movie')
    types = relationship('ProfileType', order_by="asc(ProfileType.order)") #, cascade = 'all, delete-orphan')

    def to_dict(self, deep = None, exclude = None):
        if not exclude: exclude = []
        if not deep: deep = {}

        orig_dict = super(Profile, self).to_dict(deep = deep, exclude = exclude)
        orig_dict['core'] = orig_dict.get('core') or False
        orig_dict['hide'] = orig_dict.get('hide') or False

        return orig_dict


class Category(Base, TableHelper):
    __tablename__ = 'category'
    id = Column(Integer, primary_key = True)

    """"""

    #using_options(order_by = 'order')

    label = Column(Unicode(50))
    order = Column(Integer, default = 0, index = True)
    required = Column(Unicode(255))
    preferred = Column(Unicode(255))
    ignored = Column(Unicode(255))
    destination = Column(Unicode(255))

    movie = relationship('Movie')


class ProfileType(Base, TableHelper):
    __tablename__ = 'profiletype'
    id = Column(Integer, primary_key = True)

    """"""

    #using_options(order_by = 'order')

    order = Column(Integer, default = 0, index = True)
    finish = Column(Boolean, default = True)
    wait_for = Column(Integer, default = 0)

    quality_id = Column(Integer, ForeignKey('quality.id'), index = True)
    quality = relationship('Quality')

    profile_id = Column(Integer, ForeignKey('profile.id'), index = True)
    profile = relationship('Profile')


class File(Base, TableHelper):
    __tablename__ = 'file'
    id = Column(Integer, primary_key = True)

    """File that belongs to a release."""

    path = Column(Unicode(255), nullable = False, unique = True)
    part = Column(Integer, default = 1)
    available = Column(Boolean, default = True)

    type_id = Column(Integer, ForeignKey('filetype.id'), index = True)
    type = relationship('FileType')

    properties = relationship('FileProperty')

    movie = relationship('Movie', secondary = movie_files)
    release = relationship('Release', secondary = release_files)
    library = relationship('Library', secondary = library_files)


class FileType(Base, TableHelper):
    __tablename__ = 'filetype'
    id = Column(Integer, primary_key = True)

    """Types could be trailer, subtitle, movie, partial movie etc."""

    identifier = Column(String(20), unique = True)
    type = Column(Unicode(20))
    name = Column(Unicode(50), nullable = False)

    files = relationship('File')


class FileProperty(Base, TableHelper):
    __tablename__ = 'fileproperty'
    id = Column(Integer, primary_key = True)

    """Properties that can be bound to a file for off-line usage"""

    identifier = Column(String(20), index = True)
    value = Column(Unicode(255), nullable = False)

    file_id = Column(Integer, ForeignKey('file.id'), index = True)
    file = relationship('File')


class Notification(Base, TableHelper):
    __tablename__ = 'notification'
    id = Column(Integer, primary_key = True)

    """"""

    #using_options(order_by = 'added')

    added = Column(Integer, default = lambda: int(time.time()), index = True)
    read = Column(Boolean, default = False, index = True)
    message = Column(Unicode(255))
    data = Column(JsonType)


class Properties(Base, TableHelper):
    __tablename__ = 'properties'
    id = Column(Integer, primary_key = True)

    """"""

    identifier = Column(String(50), index = True)
    value = Column(Unicode(255), nullable = False)


def setup():
    """Setup the database and create the tables that don't exists yet"""
    from couchpotato.environment import Env

    engine = Env.getEngine()
    Base.metadata.create_all(engine)

    try:
        engine.execute("PRAGMA journal_mode = WAL")
        engine.execute("PRAGMA temp_store = MEMORY")
    except:
        pass
