from migrate.changeset.schema import create_column
from sqlalchemy.schema import MetaData, Column, Table
from sqlalchemy.types import Integer

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    threed_column = Column('threed', Integer)
    resource = Table('profiletype', meta, threed_column)

    create_column(threed_column, resource)

def downgrade(migrate_engine):
    pass
