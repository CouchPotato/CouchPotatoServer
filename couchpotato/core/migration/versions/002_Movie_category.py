from migrate.changeset.schema import create_column
from sqlalchemy.schema import MetaData, Column, Table, Index
from sqlalchemy.types import Integer

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    category_column = Column('category_id', Integer)
    movie = Table('movie', meta, category_column)
    create_column(category_column, movie)
    Index('ix_movie_category_id', movie.c.category_id).create()


def downgrade(migrate_engine):
    pass
