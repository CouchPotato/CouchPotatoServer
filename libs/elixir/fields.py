'''
This module provides support for defining the fields (columns) of your
entities. Elixir currently supports two syntaxes to do so: the default
`Attribute-based syntax`_ as well as the has_field_ DSL statement.

Attribute-based syntax
----------------------

Here is a quick example of how to use the object-oriented syntax.

.. sourcecode:: python

    class Person(Entity):
        id = Field(Integer, primary_key=True)
        name = Field(String(50), required=True)
        ssn = Field(String(50), unique=True)
        biography = Field(Text)
        join_date = Field(DateTime, default=datetime.datetime.now)
        photo = Field(Binary, deferred=True)
        _email = Field(String(20), colname='email', synonym='email')

        def _set_email(self, email):
           self._email = email
        def _get_email(self):
           return self._email
        email = property(_get_email, _set_email)


The Field class takes one mandatory argument, which is its type. Please refer
to SQLAlchemy documentation for a list of `types supported by SQLAlchemy
<http://www.sqlalchemy.org/docs/05/reference/sqlalchemy/types.html>`_.

Following that first mandatory argument, fields can take any number of
optional keyword arguments. Please note that all the **arguments** that are
**not specifically processed by Elixir**, as mentioned in the documentation
below **are passed on to the SQLAlchemy ``Column`` object**. Please refer to
the `SQLAlchemy Column object's documentation
<http://www.sqlalchemy.org/docs/05/reference/sqlalchemy/schema.html
#sqlalchemy.schema.Column>`_ for more details about other
supported keyword arguments.

The following Elixir-specific arguments are supported:

+-------------------+---------------------------------------------------------+
| Argument Name     | Description                                             |
+===================+=========================================================+
| ``required``      | Specify whether or not this field can be set to None    |
|                   | (left without a value). Defaults to ``False``, unless   |
|                   | the field is a primary key.                             |
+-------------------+---------------------------------------------------------+
| ``colname``       | Specify a custom name for the column of this field. By  |
|                   | default the column will have the same name as the       |
|                   | attribute.                                              |
+-------------------+---------------------------------------------------------+
| ``deferred``      | Specify whether this particular column should be        |
|                   | fetched by default (along with the other columns) when  |
|                   | an instance of the entity is fetched from the database  |
|                   | or rather only later on when this particular column is  |
|                   | first referenced. This can be useful when one wants to  |
|                   | avoid loading a large text or binary field into memory  |
|                   | when its not needed. Individual columns can be lazy     |
|                   | loaded by themselves (by using ``deferred=True``)       |
|                   | or placed into groups that lazy-load together (by using |
|                   | ``deferred`` = `"group_name"`).                         |
+-------------------+---------------------------------------------------------+
| ``synonym``       | Specify a synonym name for this field. The field will   |
|                   | also be usable under that name in keyword-based Query   |
|                   | functions such as filter_by. The Synonym class (see the |
|                   | `properties` module) provides a similar functionality   |
|                   | with an (arguably) nicer syntax, but a limited scope.   |
+-------------------+---------------------------------------------------------+

has_field
---------

The `has_field` statement allows you to define fields one at a time.

The first argument is the name of the field, the second is its type. Following
these, any number of keyword arguments can be specified for additional
behavior. The following arguments are supported:

+-------------------+---------------------------------------------------------+
| Argument Name     | Description                                             |
+===================+=========================================================+
| ``through``       | Specify a relation name to go through. This field will  |
|                   | not exist as a column on the database but will be a     |
|                   | property which automatically proxy values to the        |
|                   | ``attribute`` attribute of the object pointed to by the |
|                   | relation. If the ``attribute`` argument is not present, |
|                   | the name of the current field will be used. In an       |
|                   | has_field statement, you can only proxy through a       |
|                   | belongs_to or an has_one relationship.                  |
+-------------------+---------------------------------------------------------+
| ``attribute``     | Name of the "endpoint" attribute to proxy to. This      |
|                   | should only be used in combination with the ``through`` |
|                   | argument.                                               |
+-------------------+---------------------------------------------------------+


Here is a quick example of how to use ``has_field``.

.. sourcecode:: python

    class Person(Entity):
        has_field('id', Integer, primary_key=True)
        has_field('name', String(50))
'''
from sqlalchemy import Column
from sqlalchemy.orm import deferred, synonym
from sqlalchemy.ext.associationproxy import association_proxy

from elixir.statements import ClassMutator
from elixir.properties import Property

__doc_all__ = ['Field']


class Field(Property):
    '''
    Represents the definition of a 'field' on an entity.

    This class represents a column on the table where the entity is stored.
    '''

    def __init__(self, type, *args, **kwargs):
        super(Field, self).__init__()

        self.colname = kwargs.pop('colname', None)
        self.synonym = kwargs.pop('synonym', None)
        self.deferred = kwargs.pop('deferred', False)
        if 'required' in kwargs:
            kwargs['nullable'] = not kwargs.pop('required')
        self.type = type
        self.primary_key = kwargs.get('primary_key', False)

        self.column = None
        self.property = None

        self.args = args
        self.kwargs = kwargs

    def attach(self, entity, name):
        # If no colname was defined (through the 'colname' kwarg), set
        # it to the name of the attr.
        if self.colname is None:
            self.colname = name
        super(Field, self).attach(entity, name)

    def create_pk_cols(self):
        if self.primary_key:
            self.create_col()

    def create_non_pk_cols(self):
        if not self.primary_key:
            self.create_col()

    def create_col(self):
        self.column = Column(self.colname, self.type,
                             *self.args, **self.kwargs)
        self.add_table_column(self.column)

    def create_properties(self):
        if self.deferred:
            group = None
            if isinstance(self.deferred, basestring):
                group = self.deferred
            self.property = deferred(self.column, group=group)
        elif self.name != self.colname:
            # if the property name is different from the column name, we need
            # to add an explicit property (otherwise nothing is needed as it's
            # done automatically by SA)
            self.property = self.column

        if self.property is not None:
            self.add_mapper_property(self.name, self.property)

        if self.synonym:
            self.add_mapper_property(self.synonym, synonym(self.name))


def has_field_handler(entity, name, *args, **kwargs):
    if 'through' in kwargs:
        setattr(entity, name,
                association_proxy(kwargs.pop('through'),
                                  kwargs.pop('attribute', name),
                                  **kwargs))
        return
    field = Field(*args, **kwargs)
    field.attach(entity, name)

has_field = ClassMutator(has_field_handler)
