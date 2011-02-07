from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.schema import ThreadLocalMetaData
from elixir import *

engine = None
session = scoped_session(sessionmaker(autoflush=True, transactional=True))
metadata


class Language(Entity):
    name = OneToMany("LanguageName")


class LanguageName(Entity):
    translation_id = Field(Integer, primary_key=True)
    language = ManyToOne('Language', primary_key=True)
    text = Field(Unicode(20), unique=True)


class Provider(Entity):
    url = Field(String(20), unique=True)


class ExternalMovieId(Entity):
    provider = ManyToOne('Provider')
    value = Field(Unicode(40))
    movie = ManyToOne('Movie')
    # such as IMDB's, maybe some use text -> long


class MovieTitle(Entity):
    language = ManyToOne('Language')
    movie = ManyToOne('Movie')
    title = Field(UnicodeText)

    def __init__(self, title, movie=None):
        self.title = unicode(title)
        self.movie = movie

class Movie(Entity):
    titles = OneToMany('MovieTitle', lazy=False)
    plot = Field(UnicodeText)
    year = Field(Integer)
    tagline = Field(UnicodeText(255))
    genres = ManyToMany('Genre')
    identifiers = OneToMany('ExternalMovieId')
    characters = ManyToMany('Character')

    def __init__(self, title, year):
        try:
            title = unicode(title)
            self.titles.append(MovieTitle(title))
        except TypeError:
            pass


class Character(Entity):
    names = OneToMany('CharacterName', required=True)
    movies = ManyToMany('Movie')


class CharacterName(Entity):
    language = ManyToOne('Language')
    character = ManyToOne('Character')


class AssociatedPeople(Entity):
    directors = ManyToMany('Person')
    screenwriters = ManyToMany('Person')
    actors = ManyToMany('Person')


class AspectRatio(Entity):
    name = Field(Unicode(20), required=True, unique=True)
    ratio = Field(Float)
    movies = ManyToMany('Movie')
    # The Dark Knight has multiple...
    
class Specification(Entity):
    language = ManyToOne('Language')
    color = Field(Boolean)


class Genre(Entity):
    name = Field(UnicodeText(255))


class Person(Entity):
    name = Field(UnicodeText(50))
    birthday = Field(Date)


class Rating(Entity):
    name = Field(UnicodeText(40))
    position = Field(Float)
    movies = ManyToMany('Movie')

    def __cmp__(self, other):
        if self.position < other.position:
            return -1
        elif self.primary_key > other.position:
            return 1
        else:
            return 0


class AgeRating(Entity):
    name = Field(UnicodeText(40))
    position = Field(Float)
    movies = ManyToMany('Movie')

    def __cmp__(self, other):
        if self.position < other.position:
            return -1
        elif self.primary_key > other.position:
            return 1
        else:
            return 0


def doctest(engine=None):
    """Test
    >>> from couchpotato import model
    >>> model.metadata.bind = "sqlite:///:memory:"
    >>> model.setup_all()
    >>> model.setup_all()
    """
    pass
