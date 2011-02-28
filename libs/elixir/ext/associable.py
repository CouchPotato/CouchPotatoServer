'''
Associable Elixir Statement Generator

==========
Associable
==========

About Polymorphic Associations
------------------------------

A frequent pattern in database schemas is the has_and_belongs_to_many, or a
many-to-many table. Quite often multiple tables will refer to a single one
creating quite a few many-to-many intermediate tables.

Polymorphic associations lower the amount of many-to-many tables by setting up
a table that allows relations to any other table in the database, and relates
it to the associable table. In some implementations, this layout does not
enforce referential integrity with database foreign key constraints, this
implementation uses an additional many-to-many table with foreign key
constraints to avoid this problem.

.. note:
    SQLite does not support foreign key constraints, so referential integrity
    can only be enforced using database backends with such support.

Elixir Statement Generator for Polymorphic Associations
-------------------------------------------------------

The ``associable`` function generates the intermediary tables for an Elixir
entity that should be associable with other Elixir entities and returns an
Elixir Statement for use with them. This automates the process of creating the
polymorphic association tables and ensuring their referential integrity.

Matching select_XXX and select_by_XXX are also added to the associated entity
which allow queries to be run for the associated objects.

Example usage:

.. sourcecode:: python

    class Tag(Entity):
        name = Field(Unicode)

    acts_as_taggable = associable(Tag)

    class Entry(Entity):
        title = Field(Unicode)
        acts_as_taggable('tags')

    class Article(Entity):
        title = Field(Unicode)
        acts_as_taggable('tags')

Or if one of the entities being associated should only have a single member of
the associated table:

.. sourcecode:: python

    class Address(Entity):
        street = Field(String(130))
        city = Field(String(100))

    is_addressable = associable(Address, 'addresses')

    class Person(Entity):
        name = Field(Unicode)
        orders = OneToMany('Order')
        is_addressable()

    class Order(Entity):
        order_num = Field(primary_key=True)
        item_count = Field(Integer)
        person = ManyToOne('Person')
        is_addressable('address', uselist=False)

    home = Address(street='123 Elm St.', city='Spooksville')
    user = Person(name='Jane Doe')
    user.addresses.append(home)

    neworder = Order(item_count=4)
    neworder.address = home
    user.orders.append(neworder)

    # Queries using the added helpers
    Person.select_by_addresses(city='Cupertino')
    Person.select_addresses(and_(Address.c.street=='132 Elm St',
                                 Address.c.city=='Smallville'))

Statement Options
-----------------

The generated Elixir Statement has several options available:

+---------------+-------------------------------------------------------------+
| Option Name   | Description                                                 |
+===============+=============================================================+
| ``name``      | Specify a custom name for the Entity attribute. This is     |
|               | used to declare the attribute used to access the associated |
|               | table values. Otherwise, the name will use the plural_name  |
|               | provided to the associable call.                            |
+---------------+-------------------------------------------------------------+
| ``uselist``   | Whether or not the associated table should be represented   |
|               | as a list, or a single property. It should be set to False  |
|               | when the entity should only have a single associated        |
|               | entity. Defaults to True.                                   |
+---------------+-------------------------------------------------------------+
| ``lazy``      | Determines eager loading of the associated entity objects.  |
|               | Defaults to False, to indicate that they should not be      |
|               | lazily loaded.                                              |
+---------------+-------------------------------------------------------------+
'''
from elixir.statements import Statement
import sqlalchemy as sa

__doc_all__ = ['associable']


def associable(assoc_entity, plural_name=None, lazy=True):
    '''
    Generate an associable Elixir Statement
    '''
    interface_name = assoc_entity._descriptor.tablename
    able_name = interface_name + 'able'

    if plural_name:
        attr_name = "%s_rel" % plural_name
    else:
        plural_name = interface_name
        attr_name = "%s_rel" % interface_name

    class GenericAssoc(object):

        def __init__(self, tablename):
            self.type = tablename

    #TODO: inherit from entity builder
    class Associable(object):
        """An associable Elixir Statement object"""

        def __init__(self, entity, name=None, uselist=True, lazy=True):
            self.entity = entity
            self.lazy = lazy
            self.uselist = uselist

            if name is None:
                self.name = plural_name
            else:
                self.name = name

        def after_table(self):
            col = sa.Column('%s_assoc_id' % interface_name, sa.Integer,
                            sa.ForeignKey('%s.id' % able_name))
            self.entity._descriptor.add_column(col)

            if not hasattr(assoc_entity, '_assoc_table'):
                metadata = assoc_entity._descriptor.metadata
                association_table = sa.Table("%s" % able_name, metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('type', sa.String(40), nullable=False),
                )
                tablename =  "%s_to_%s" % (able_name, interface_name)
                association_to_table = sa.Table(tablename, metadata,
                    sa.Column('assoc_id', sa.Integer,
                              sa.ForeignKey(association_table.c.id,
                                            ondelete="CASCADE"),
                              primary_key=True),
                    #FIXME: this assumes a single id col
                    sa.Column('%s_id' % interface_name, sa.Integer,
                              sa.ForeignKey(assoc_entity.table.c.id,
                                            ondelete="RESTRICT"),
                              primary_key=True),
                )

                assoc_entity._assoc_table = association_table
                assoc_entity._assoc_to_table = association_to_table

        def after_mapper(self):
            if not hasattr(assoc_entity, '_assoc_mapper'):
                assoc_entity._assoc_mapper = sa.orm.mapper(
                    GenericAssoc, assoc_entity._assoc_table, properties={
                        'targets': sa.orm.relation(
                                       assoc_entity,
                                       secondary=assoc_entity._assoc_to_table,
                                       lazy=lazy, backref='associations',
                                       order_by=assoc_entity.mapper.order_by)
                })

            entity = self.entity
            entity.mapper.add_property(
                attr_name,
                sa.orm.relation(GenericAssoc, lazy=self.lazy,
                                backref='_backref_%s' % entity.table.name)
            )

            if self.uselist:
                def get(self):
                    if getattr(self, attr_name) is None:
                        setattr(self, attr_name,
                                GenericAssoc(entity.table.name))
                    return getattr(self, attr_name).targets
                setattr(entity, self.name, property(get))
            else:
                # scalar based property decorator
                def get(self):
                    attr = getattr(self, attr_name)
                    if attr is not None:
                        return attr.targets[0]
                    else:
                        return None
                def set(self, value):
                    if getattr(self, attr_name) is None:
                        setattr(self, attr_name,
                                GenericAssoc(entity.table.name))
                    getattr(self, attr_name).targets = [value]
                setattr(entity, self.name, property(get, set))

            # self.name is both set via mapper synonym and the python
            # property, but that's how synonym properties work.
            # adding synonym property after "real" property otherwise it
            # breaks when using SQLAlchemy > 0.4.1
            entity.mapper.add_property(self.name, sa.orm.synonym(attr_name))

            # add helper methods
            def select_by(cls, **kwargs):
                return cls.query.join([attr_name, 'targets']) \
                                .filter_by(**kwargs).all()
            setattr(entity, 'select_by_%s' % self.name, classmethod(select_by))

            def select(cls, *args, **kwargs):
                return cls.query.join([attr_name, 'targets']) \
                                .filter(*args, **kwargs).all()
            setattr(entity, 'select_%s' % self.name, classmethod(select))

    return Statement(Associable)
