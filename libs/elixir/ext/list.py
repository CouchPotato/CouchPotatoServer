'''
This extension is DEPRECATED. Please use the orderinglist SQLAlchemy
extension instead.

For details:
http://www.sqlalchemy.org/docs/05/reference/ext/orderinglist.html

For an Elixir example:
http://elixir.ematia.de/trac/wiki/Recipes/UsingEntityForOrderedList
or
http://elixir.ematia.de/trac/browser/elixir/0.7.0/tests/test_o2m.py#L155



An ordered-list plugin for Elixir to help you make an entity be able to be
managed in a list-like way. Much inspiration comes from the Ruby on Rails
acts_as_list plugin, which is currently more full-featured than this plugin.

Once you flag an entity with an `acts_as_list()` statement, a column will be
added to the entity called `position` which will be an integer column that is
managed for you by the plugin.  You can pass an alternative column name to
the plugin using the `column_name` keyword argument.

In addition, your entity will get a series of new methods attached to it,
including:

+----------------------+------------------------------------------------------+
| Method Name          | Description                                          |
+======================+======================================================+
| ``move_lower``       | Move the item lower in the list                      |
+----------------------+------------------------------------------------------+
| ``move_higher``      | Move the item higher in the list                     |
+----------------------+------------------------------------------------------+
| ``move_to_bottom``   | Move the item to the bottom of the list              |
+----------------------+------------------------------------------------------+
| ``move_to_top``      | Move the item to the top of the list                 |
+----------------------+------------------------------------------------------+
| ``move_to``          | Move the item to a specific position in the list     |
+----------------------+------------------------------------------------------+


Sometimes, your entities that represent list items will be a part of different
lists. To implement this behavior, simply pass the `acts_as_list` statement a
callable that returns a "qualifier" SQLAlchemy expression. This expression will
be added to the generated WHERE clauses used by the plugin.

Example model usage:

.. sourcecode:: python

    from elixir import *
    from elixir.ext.list import acts_as_list

    class ToDo(Entity):
        subject = Field(String(128))
        owner = ManyToOne('Person')

        def qualify(self):
            return ToDo.owner_id == self.owner_id

        acts_as_list(qualifier=qualify)

    class Person(Entity):
        name = Field(String(64))
        todos = OneToMany('ToDo', order_by='position')


The above example can then be used to manage ordered todo lists for people.
Note that you must set the `order_by` property on the `Person.todo` relation in
order for the relation to respect the ordering. Here is an example of using
this model in practice:

.. sourcecode:: python

    p = Person.query.filter_by(name='Jonathan').one()
    p.todos.append(ToDo(subject='Three'))
    p.todos.append(ToDo(subject='Two'))
    p.todos.append(ToDo(subject='One'))
    session.commit(); session.clear()

    p = Person.query.filter_by(name='Jonathan').one()
    p.todos[0].move_to_bottom()
    p.todos[2].move_to_top()
    session.commit(); session.clear()

    p = Person.query.filter_by(name='Jonathan').one()
    assert p.todos[0].subject == 'One'
    assert p.todos[1].subject == 'Two'
    assert p.todos[2].subject == 'Three'


For more examples, refer to the unit tests for this plugin.
'''

from elixir.statements import Statement
from elixir.events import before_insert, before_delete
from sqlalchemy import Column, Integer, select, func, literal, and_
import warnings

__all__ = ['acts_as_list']
__doc_all__ = []


def get_entity_where(instance):
    clauses = []
    for column in instance.table.primary_key.columns:
        instance_value = getattr(instance, column.name)
        clauses.append(column == instance_value)
    return and_(*clauses)


class ListEntityBuilder(object):

    def __init__(self, entity, qualifier=None, column_name='position'):
        warnings.warn("The act_as_list extension is deprecated. Please use "
                      "SQLAlchemy's orderinglist extension instead",
                      DeprecationWarning, stacklevel=6)
        self.entity = entity
        self.qualifier_method = qualifier
        self.column_name = column_name

    def create_non_pk_cols(self):
        if self.entity._descriptor.autoload:
            for c in self.entity.table.c:
                if c.name == self.column_name:
                    self.position_column = c
            if not hasattr(self, 'position_column'):
                raise Exception(
                    "Could not find column '%s' in autoloaded table '%s', "
                    "needed by entity '%s'." % (self.column_name,
                        self.entity.table.name, self.entity.__name__))
        else:
            self.position_column = Column(self.column_name, Integer)
            self.entity._descriptor.add_column(self.position_column)

    def after_table(self):
        position_column = self.position_column
        position_column_name = self.column_name

        qualifier_method = self.qualifier_method
        if not qualifier_method:
            qualifier_method = lambda self: None

        def _init_position(self):
            s = select(
                [(func.max(position_column)+1).label('value')],
                qualifier_method(self)
            ).union(
                select([literal(1).label('value')])
            )
            a = s.alias()
            # we use a second func.max to get the maximum between 1 and the
            # real max position if any exist
            setattr(self, position_column_name, select([func.max(a.c.value)]))

            # Note that this method could be rewritten more simply like below,
            # but because this extension is going to be deprecated anyway,
            # I don't want to risk breaking something I don't want to maintain.
#            setattr(self, position_column_name, select(
#                [func.coalesce(func.max(position_column), 0) + 1],
#                qualifier_method(self)
#            ))
        _init_position = before_insert(_init_position)

        def _shift_items(self):
            self.table.update(
                and_(
                    position_column > getattr(self, position_column_name),
                    qualifier_method(self)
                ),
                values={
                    position_column : position_column - 1
                }
            ).execute()
        _shift_items = before_delete(_shift_items)

        def move_to_bottom(self):
            # move the items that were above this item up one
            self.table.update(
                and_(
                    position_column >= getattr(self, position_column_name),
                    qualifier_method(self)
                ),
                values = {
                    position_column : position_column - 1
                }
            ).execute()

            # move this item to the max position
            # MySQL does not support the correlated subquery, so we need to
            # execute the query (through scalar()). See ticket #34.
            self.table.update(
                get_entity_where(self),
                values={
                    position_column : select(
                        [func.max(position_column) + 1],
                        qualifier_method(self)
                    ).scalar()
                }
            ).execute()

        def move_to_top(self):
            self.move_to(1)

        def move_to(self, position):
            current_position = getattr(self, position_column_name)

            # determine which direction we're moving
            if position < current_position:
                where = and_(
                    position <= position_column,
                    position_column < current_position,
                    qualifier_method(self)
                )
                modifier = 1
            elif position > current_position:
                where = and_(
                    current_position < position_column,
                    position_column <= position,
                    qualifier_method(self)
                )
                modifier = -1

            # shift the items in between the current and new positions
            self.table.update(where, values = {
                position_column : position_column + modifier
            }).execute()

            # update this item's position to the desired position
            self.table.update(get_entity_where(self)) \
                      .execute(**{position_column_name: position})

        def move_lower(self):
            # replace for ex.: p.todos.insert(x + 1, p.todos.pop(x))
            self.move_to(getattr(self, position_column_name) + 1)

        def move_higher(self):
            self.move_to(getattr(self, position_column_name) - 1)


        # attach new methods to entity
        self.entity._init_position = _init_position
        self.entity._shift_items = _shift_items
        self.entity.move_lower = move_lower
        self.entity.move_higher = move_higher
        self.entity.move_to_bottom = move_to_bottom
        self.entity.move_to_top = move_to_top
        self.entity.move_to = move_to


acts_as_list = Statement(ListEntityBuilder)
