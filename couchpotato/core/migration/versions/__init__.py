"""
    Examples

        Adding a column:

            from migrate import *
            from migrate.changeset.schema import create_column
            from sqlalchemy import *

            meta = MetaData()

            def upgrade(migrate_engine):
                meta.bind = migrate_engine

                #print changeset.schema
                path_column = Column('path', String)
                resource = Table('resource', meta, path_column)

                create_column(path_column, resource)



        Adding Relation table: http://www.mail-archive.com/sqlelixir@googlegroups.com/msg02061.html

            person = Table('person', metadata, Column('id', Integer))
            person_column = Column('person_id', Integer, ForeignKey('person.id'), nullable=False)
            movie = Table('movie', metadata, person_column)
            person_constraint = ForeignKeyConstraint(['person_id'], ['person.id'], ondelete="restrict", table=movie)

"""
