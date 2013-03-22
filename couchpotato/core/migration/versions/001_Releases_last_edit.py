from migrate.changeset.schema import create_column
from sqlalchemy.schema import MetaData, Column, Table, Index
from sqlalchemy.types import Integer

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    # Change release, add last_edit and index
    last_edit_column = Column('last_edit', Integer)
    release = Table('release', meta, last_edit_column)

    create_column(last_edit_column, release)
    Index('ix_release_last_edit', release.c.last_edit).create()

    # Change movie last_edit
    last_edit_column = Column('last_edit', Integer)
    movie = Table('movie', meta, last_edit_column)
    Index('ix_movie_last_edit', movie.c.last_edit).create()


def downgrade(migrate_engine):
    pass
