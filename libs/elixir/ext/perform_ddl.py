'''
DDL statements for Elixir.

Entities having the perform_ddl statement, will automatically execute the
given DDL statement, at the given moment: ether before or after the table
creation in SQL.

The 'when' argument can be either 'before-create' or 'after-create'.
The 'statement' argument can be one of:

- a single string statement
- a list of string statements, in which case, each of them will be executed
  in turn.
- a callable which should take no argument and return either a single string
  or a list of strings.

In each string statement, you may use the special '%(fullname)s' construct,
that will be replaced with the real table name including schema, if unknown
to you. Also, self explained '%(table)s' and '%(schema)s' may be used here.

You would use this extension to handle non elixir sql statemts, like triggers
etc.

.. sourcecode:: python

    class Movie(Entity):
        title = Field(Unicode(30), primary_key=True)
        year = Field(Integer)

        perform_ddl('after-create',
                    "insert into %(fullname)s values ('Alien', 1979)")

preload_data is a more specific statement meant to preload data in your
entity table from a list of tuples (of fields values for each row).

.. sourcecode:: python

    class Movie(Entity):
        title = Field(Unicode(30), primary_key=True)
        year = Field(Integer)

        preload_data(('title', 'year'),
                     [(u'Alien', 1979), (u'Star Wars', 1977)])
        preload_data(('year', 'title'),
                     [(1982, u'Blade Runner')])
        preload_data(data=[(u'Batman', 1966)])
'''

from elixir.statements import Statement
from elixir.properties import EntityBuilder
from sqlalchemy import DDL

__all__ = ['perform_ddl', 'preload_data']
__doc_all__ = []

#
# the perform_ddl statement
#
class PerformDDLEntityBuilder(EntityBuilder):

    def __init__(self, entity, when, statement, on=None, context=None):
        self.entity = entity
        self.when = when
        self.statement = statement
        self.on = on
        self.context = context

    def after_table(self):
        statement = self.statement
        if hasattr(statement, '__call__'):
            statement = statement()
        if not isinstance(statement, list):
            statement = [statement]
        for s in statement:
            ddl = DDL(s, self.on, self.context)
            ddl.execute_at(self.when, self.entity.table)

perform_ddl = Statement(PerformDDLEntityBuilder)

#
# the preload_data statement
#
class PreloadDataEntityBuilder(EntityBuilder):

    def __init__(self, entity, columns=None, data=None):
        self.entity = entity
        self.columns = columns
        self.data = data

    def after_table(self):
        all_columns = [col.name for col in self.entity.table.columns]
        def onload(event, schema_item, connection):
            columns = self.columns
            if columns is None:
                columns = all_columns
            data = self.data
            if hasattr(data, '__call__'):
                data = data()
            insert = schema_item.insert()
            connection.execute(insert,
                [dict(zip(columns, values)) for values in data])

        self.entity.table.append_ddl_listener('after-create', onload)

preload_data = Statement(PreloadDataEntityBuilder)

