'''
A versioning plugin for Elixir.

Entities that are marked as versioned with the `acts_as_versioned` statement
will automatically have a history table created and a timestamp and version
column added to their tables. In addition, versioned entities are provided
with four new methods: revert, revert_to, compare_with and get_as_of, and one
new attribute: versions.  Entities with compound primary keys are supported.

The `versions` attribute will contain a list of previous versions of the
instance, in increasing version number order.

The `get_as_of` method will retrieve a previous version of the instance "as of"
a specified datetime. If the current version is the most recent, it will be
returned.

The `revert` method will rollback the current instance to its previous version,
if possible. Once reverted, the current instance will be expired from the
session, and you will need to fetch it again to retrieve the now reverted
instance.

The `revert_to` method will rollback the current instance to the specified
version number, if possibe. Once reverted, the current instance will be expired
from the session, and you will need to fetch it again to retrieve the now
reverted instance.

The `compare_with` method will compare the instance with a previous version. A
dictionary will be returned with each field difference as an element in the
dictionary where the key is the field name and the value is a tuple of the
format (current_value, version_value). Version instances also have a
`compare_with` method so that two versions can be compared.

Also included in the module is a `after_revert` decorator that can be used to
decorate methods on the versioned entity that will be called following that
instance being reverted.

The acts_as_versioned statement also accepts an optional `ignore` argument
that consists of a list of strings, specifying names of fields.  Changes in
those fields will not result in a version increment.  In addition, you can
pass in an optional `check_concurrent` argument, which will use SQLAlchemy's
built-in optimistic concurrency mechanisms.

Note that relationships that are stored in mapping tables will not be included
as part of the versioning process, and will need to be handled manually. Only
values within the entity's main table will be versioned into the history table.
'''

from datetime              import datetime
import inspect

from sqlalchemy            import Table, Column, and_, desc
from sqlalchemy.orm        import mapper, MapperExtension, EXT_CONTINUE, \
                                  object_session

from elixir                import Integer, DateTime
from elixir.statements     import Statement
from elixir.properties     import EntityBuilder
from elixir.entity         import getmembers

__all__ = ['acts_as_versioned', 'after_revert']
__doc_all__ = []

#
# utility functions
#

def get_entity_where(instance):
    clauses = []
    for column in instance.table.primary_key.columns:
        instance_value = getattr(instance, column.name)
        clauses.append(column==instance_value)
    return and_(*clauses)


def get_history_where(instance):
    clauses = []
    history_columns = instance.__history_table__.primary_key.columns
    for column in instance.table.primary_key.columns:
        instance_value = getattr(instance, column.name)
        history_column = getattr(history_columns, column.name)
        clauses.append(history_column==instance_value)
    return and_(*clauses)


#
# a mapper extension to track versions on insert, update, and delete
#

class VersionedMapperExtension(MapperExtension):
    def before_insert(self, mapper, connection, instance):
        version_colname, timestamp_colname = \
            instance.__class__.__versioned_column_names__
        setattr(instance, version_colname, 1)
        setattr(instance, timestamp_colname, datetime.now())
        return EXT_CONTINUE

    def before_update(self, mapper, connection, instance):
        old_values = instance.table.select(get_entity_where(instance)) \
                                   .execute().fetchone()

        # SA might've flagged this for an update even though it didn't change.
        # This occurs when a relation is updated, thus marking this instance
        # for a save/update operation. We check here against the last version
        # to ensure we really should save this version and update the version
        # data.
        ignored = instance.__class__.__ignored_fields__
        version_colname, timestamp_colname = \
            instance.__class__.__versioned_column_names__
        for key in instance.table.c.keys():
            if key in ignored:
                continue
            if getattr(instance, key) != old_values[key]:
                # the instance was really updated, so we create a new version
                dict_values = dict(old_values.items())
                connection.execute(
                    instance.__class__.__history_table__.insert(), dict_values)
                old_version = getattr(instance, version_colname)
                setattr(instance, version_colname, old_version + 1)
                setattr(instance, timestamp_colname, datetime.now())
                break

        return EXT_CONTINUE

    def before_delete(self, mapper, connection, instance):
        connection.execute(instance.__history_table__.delete(
            get_history_where(instance)
        ))
        return EXT_CONTINUE


versioned_mapper_extension = VersionedMapperExtension()


#
# the acts_as_versioned statement
#

class VersionedEntityBuilder(EntityBuilder):

    def __init__(self, entity, ignore=None, check_concurrent=False,
                 column_names=None):
        self.entity = entity
        self.add_mapper_extension(versioned_mapper_extension)
        #TODO: we should rather check that the version_id_col isn't set
        # externally
        self.check_concurrent = check_concurrent

        # Changes in these fields will be ignored
        if column_names is None:
            column_names = ['version', 'timestamp']
        entity.__versioned_column_names__ = column_names
        if ignore is None:
            ignore = []
        ignore.extend(column_names)
        entity.__ignored_fields__ = ignore

    def create_non_pk_cols(self):
        # add a version column to the entity, along with a timestamp
        version_colname, timestamp_colname = \
            self.entity.__versioned_column_names__
        #XXX: fail in case the columns already exist?
        #col_names = [col.name for col in self.entity._descriptor.columns]
        #if version_colname not in col_names:
        self.add_table_column(Column(version_colname, Integer))
        #if timestamp_colname not in col_names:
        self.add_table_column(Column(timestamp_colname, DateTime))

        # add a concurrent_version column to the entity, if required
        if self.check_concurrent:
            self.entity._descriptor.version_id_col = 'concurrent_version'

    # we copy columns from the main entity table, so we need it to exist first
    def after_table(self):
        entity = self.entity
        version_colname, timestamp_colname = \
            entity.__versioned_column_names__

        # look for events
        after_revert_events = []
        for name, func in getmembers(entity, inspect.ismethod):
            if getattr(func, '_elixir_after_revert', False):
                after_revert_events.append(func)

        # create a history table for the entity
        skipped_columns = [version_colname]
        if self.check_concurrent:
            skipped_columns.append('concurrent_version')

        columns = [
            column.copy() for column in entity.table.c
            if column.name not in skipped_columns
        ]
        columns.append(Column(version_colname, Integer, primary_key=True))
        table = Table(entity.table.name + '_history', entity.table.metadata,
            *columns
        )
        entity.__history_table__ = table

        # create an object that represents a version of this entity
        class Version(object):
            pass

        # map the version class to the history table for this entity
        Version.__name__ = entity.__name__ + 'Version'
        Version.__versioned_entity__ = entity
        mapper(Version, entity.__history_table__)

        version_col = getattr(table.c, version_colname)
        timestamp_col = getattr(table.c, timestamp_colname)

        # attach utility methods and properties to the entity
        def get_versions(self):
            v = object_session(self).query(Version) \
                                    .filter(get_history_where(self)) \
                                    .order_by(version_col) \
                                    .all()
            # history contains all the previous records.
            # Add the current one to the list to get all the versions
            v.append(self)
            return v

        def get_as_of(self, dt):
            # if the passed in timestamp is older than our current version's
            # time stamp, then the most recent version is our current version
            if getattr(self, timestamp_colname) < dt:
                return self

            # otherwise, we need to look to the history table to get our
            # older version
            sess = object_session(self)
            query = sess.query(Version) \
                        .filter(and_(get_history_where(self),
                                     timestamp_col <= dt)) \
                        .order_by(desc(timestamp_col)).limit(1)
            return query.first()

        def revert_to(self, to_version):
            if isinstance(to_version, Version):
                to_version = getattr(to_version, version_colname)

            old_version = table.select(and_(
                get_history_where(self),
                version_col == to_version
            )).execute().fetchone()

            entity.table.update(get_entity_where(self)).execute(
                dict(old_version.items())
            )

            table.delete(and_(get_history_where(self),
                              version_col >= to_version)).execute()
            self.expire()
            for event in after_revert_events:
                event(self)

        def revert(self):
            assert getattr(self, version_colname) > 1
            self.revert_to(getattr(self, version_colname) - 1)

        def compare_with(self, version):
            differences = {}
            for column in self.table.c:
                if column.name in (version_colname, 'concurrent_version'):
                    continue
                this = getattr(self, column.name)
                that = getattr(version, column.name)
                if this != that:
                    differences[column.name] = (this, that)
            return differences

        entity.versions = property(get_versions)
        entity.get_as_of = get_as_of
        entity.revert_to = revert_to
        entity.revert = revert
        entity.compare_with = compare_with
        Version.compare_with = compare_with

acts_as_versioned = Statement(VersionedEntityBuilder)


def after_revert(func):
    """
    Decorator for watching for revert events.
    """
    func._elixir_after_revert = True
    return func


