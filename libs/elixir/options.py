'''
This module provides support for defining several options on your Elixir
entities.  There are three different kinds of options that can be set
up, and for this there are three different statements: using_options_,
using_table_options_ and using_mapper_options_.

Alternatively, these options can be set on all Elixir entities by modifying
the `options_defaults` dictionary before defining any entity.

`using_options`
---------------
The 'using_options' DSL statement allows you to set up some additional
behaviors on your model objects, including table names, ordering, and
more.  To specify an option, simply supply the option as a keyword
argument onto the statement, as follows:

.. sourcecode:: python

    class Person(Entity):
        name = Field(Unicode(64))

        using_options(shortnames=True, order_by='name')

The list of supported arguments are as follows:

+---------------------+-------------------------------------------------------+
| Option Name         | Description                                           |
+=====================+=======================================================+
| ``inheritance``     | Specify the type of inheritance this entity must use. |
|                     | It can be one of ``single``, ``concrete`` or          |
|                     | ``multi``. Defaults to ``single``.                    |
|                     | Note that polymorphic concrete inheritance is         |
|                     | currently not implemented. See:                       |
|                     | http://www.sqlalchemy.org/docs/05/mappers.html        |
|                     | #mapping-class-inheritance-hierarchies for an         |
|                     | explanation of the different kinds of inheritances.   |
+---------------------+-------------------------------------------------------+
| ``abstract``        | Set 'abstract'=True to declare abstract entity.       |
|                     | Abstract base classes are useful when you want to put |
|                     | some common information into a number of other        |
|                     | entities. Abstract entity will not be used to create  |
|                     | any database table. Instead, when it is used as a base|
|                     | class for other entity, its fields will be added to   |
|                     | those of the child class.                             |
+---------------------+-------------------------------------------------------+
| ``polymorphic``     | Whether the inheritance should be polymorphic or not. |
|                     | Defaults to ``True``. The column used to store the    |
|                     | type of each row is named "row_type" by default. You  |
|                     | can change this by passing the desired name for the   |
|                     | column to this argument.                              |
+---------------------+-------------------------------------------------------+
| ``identity``        | Specify a custom polymorphic identity. When using     |
|                     | polymorphic inheritance, this value (usually a        |
|                     | string) will represent this particular entity (class) |
|                     | . It will be used to differentiate it from other      |
|                     | entities (classes) in your inheritance hierarchy when |
|                     | loading from the database instances of different      |
|                     | entities in that hierarchy at the same time.          |
|                     | This value will be stored by default in the           |
|                     | "row_type" column of the entity's table (see above).  |
|                     | You can either provide a                              |
|                     | plain string or a callable. The callable will be      |
|                     | given the entity (ie class) as argument and must      |
|                     | return a value (usually a string) representing the    |
|                     | polymorphic identity of that entity.                  |
|                     | By default, this value is automatically generated: it |
|                     | is the name of the entity lower-cased.                |
+---------------------+-------------------------------------------------------+
| ``metadata``        | Specify a custom MetaData for this entity.            |
|                     | By default, entities uses the global                  |
|                     | ``elixir.metadata``.                                  |
|                     | This option can also be set for all entities of a     |
|                     | module by setting the ``__metadata__`` attribute of   |
|                     | that module.                                          |
+---------------------+-------------------------------------------------------+
| ``autoload``        | Automatically load column definitions from the        |
|                     | existing database table.                              |
+---------------------+-------------------------------------------------------+
| ``tablename``       | Specify a custom tablename. You can either provide a  |
|                     | plain string or a callable. The callable will be      |
|                     | given the entity (ie class) as argument and must      |
|                     | return a string representing the name of the table    |
|                     | for that entity. By default, the tablename is         |
|                     | automatically generated: it is a concatenation of the |
|                     | full module-path to the entity and the entity (class) |
|                     | name itself. The result is lower-cased and separated  |
|                     | by underscores ("_"), eg.: for an entity named        |
|                     | "MyEntity" in the module "project1.model", the        |
|                     | generated table name will be                          |
|                     | "project1_model_myentity".                            |
+---------------------+-------------------------------------------------------+
| ``shortnames``      | Specify whether or not the automatically generated    |
|                     | table names include the full module-path              |
|                     | to the entity. If ``shortnames`` is ``True``, only    |
|                     | the entity name is used. Defaults to ``False``.       |
+---------------------+-------------------------------------------------------+
| ``auto_primarykey`` | If given as string, it will represent the             |
|                     | auto-primary-key's column name.  If this option       |
|                     | is True, it will allow auto-creation of a primary     |
|                     | key if there's no primary key defined for the         |
|                     | corresponding entity.  If this option is False,       |
|                     | it will disallow auto-creation of a primary key.      |
|                     | Defaults to ``True``.                                 |
+---------------------+-------------------------------------------------------+
| ``version_id_col``  | If this option is True, it will create a version      |
|                     | column automatically using the default name. If given |
|                     | as string, it will create the column using that name. |
|                     | This can be used to prevent concurrent modifications  |
|                     | to the entity's table rows (i.e. it will raise an     |
|                     | exception if it happens). Defaults to ``False``.      |
+---------------------+-------------------------------------------------------+
| ``order_by``        | How to order select results. Either a string or a     |
|                     | list of strings, composed of the field name,          |
|                     | optionally lead by a minus (for descending order).    |
+---------------------+-------------------------------------------------------+
| ``session``         | Specify a custom contextual session for this entity.  |
|                     | By default, entities uses the global                  |
|                     | ``elixir.session``.                                   |
|                     | This option takes a ``ScopedSession`` object or       |
|                     | ``None``. In the later case your entity will be       |
|                     | mapped using a non-contextual mapper which requires   |
|                     | manual session management, as seen in pure SQLAlchemy.|
|                     | This option can also be set for all entities of a     |
|                     | module by setting the ``__session__`` attribute of    |
|                     | that module.                                          |
+---------------------+-------------------------------------------------------+
| ``autosetup``       | DEPRECATED. Specify whether that entity will contain  |
|                     | automatic setup triggers.                             |
|                     | That is if this entity will be                        |
|                     | automatically setup (along with all other entities    |
|                     | which were already declared) if any of the following  |
|                     | condition happen: some of its attributes are accessed |
|                     | ('c', 'table', 'mapper' or 'query'), instanciated     |
|                     | (called) or the create_all method of this entity's    |
|                     | metadata is called. Defaults to ``False``.            |
+---------------------+-------------------------------------------------------+
| ``allowcoloverride``| Specify whether it is allowed to override columns.    |
|                     | By default, Elixir forbids you to add a column to an  |
|                     | entity's table which already exist in that table. If  |
|                     | you set this option to ``True`` it will skip that     |
|                     | check. Use with care as it is easy to shoot oneself   |
|                     | in the foot when overriding columns.                  |
+---------------------+-------------------------------------------------------+

For examples, please refer to the examples and unit tests.

`using_table_options`
---------------------
The 'using_table_options' DSL statement allows you to set up some
additional options on your entity table. It is meant only to handle the
options which are not supported directly by the 'using_options' statement.
By opposition to the 'using_options' statement, these options are passed
directly to the underlying SQLAlchemy Table object (both non-keyword arguments
and keyword arguments) without any processing.

For further information, please refer to the `SQLAlchemy table's documentation
<http://www.sqlalchemy.org/docs/05/reference/sqlalchemy/schema.html
#sqlalchemy.schema.Table>`_.

You might also be interested in the section about `constraints
<http://www.sqlalchemy.org/docs/05/metadata.html
#defining-constraints-and-indexes>`_.

`using_mapper_options`
----------------------
The 'using_mapper_options' DSL statement allows you to set up some
additional options on your entity mapper. It is meant only to handle the
options which are not supported directly by the 'using_options' statement.
By opposition to the 'using_options' statement, these options are passed
directly to the underlying SQLAlchemy mapper (as keyword arguments)
without any processing.

For further information, please refer to the `SQLAlchemy mapper
function's documentation
<http://www.sqlalchemy.org/docs/05/reference/orm/mapping.html
#sqlalchemy.orm.mapper>`_.

`using_options_defaults`
------------------------
The 'using_options_defaults' DSL statement allows you to set up some
default options on a custom base class. These will be used as the default value
for options of all its subclasses. Note that any option not set within the
using_options_defaults (nor specifically on a particular Entity) will use the
global defaults, so you don't have to provide a default value for all options,
but only those you want to change. Please also note that this statement does
not work on normal entities, and the normal using_options statement does not
work on base classes (because normal options do not and should not propagate to
the children classes).
'''

from sqlalchemy import Integer, String

from elixir.statements import ClassMutator

__doc_all__ = ['options_defaults']

OLD_M2MCOL_NAMEFORMAT = "%(tablename)s_%(key)s%(numifself)s"
ALTERNATE_M2MCOL_NAMEFORMAT = "%(inversename)s_%(key)s"

def default_m2m_column_formatter(data):
    if data['selfref']:
        return ALTERNATE_M2MCOL_NAMEFORMAT % data
    else:
        return OLD_M2MCOL_NAMEFORMAT % data

NEW_M2MCOL_NAMEFORMAT = default_m2m_column_formatter

# format constants
FKCOL_NAMEFORMAT = "%(relname)s_%(key)s"
M2MCOL_NAMEFORMAT = NEW_M2MCOL_NAMEFORMAT
CONSTRAINT_NAMEFORMAT = "%(tablename)s_%(colnames)s_fk"
MULTIINHERITANCECOL_NAMEFORMAT = "%(entity)s_%(key)s"

# other global constants
DEFAULT_AUTO_PRIMARYKEY_NAME = "id"
DEFAULT_AUTO_PRIMARYKEY_TYPE = Integer
DEFAULT_VERSION_ID_COL_NAME = "row_version"
DEFAULT_POLYMORPHIC_COL_NAME = "row_type"
POLYMORPHIC_COL_SIZE = 40
POLYMORPHIC_COL_TYPE = String(POLYMORPHIC_COL_SIZE)

# debugging/migration help
MIGRATION_TO_07_AID = False

#
options_defaults = dict(
    abstract=False,
    autosetup=False,
    inheritance='single',
    polymorphic=True,
    identity=None,
    autoload=False,
    tablename=None,
    shortnames=False,
    auto_primarykey=True,
    version_id_col=False,
    allowcoloverride=False,
    order_by=None,
    resolve_root=None,
    mapper_options={},
    table_options={}
)

valid_options = options_defaults.keys() + [
    'metadata',
    'session',
    'collection'
]


def using_options_defaults_handler(entity, **kwargs):
    for kwarg in kwargs:
        if kwarg not in valid_options:
            raise Exception("'%s' is not a valid option for Elixir entities."
                            % kwarg)

    # We use __dict__ instead of hasattr to not check its presence within the
    # parent, and thus update the parent dict instead of creating a local dict.
    if not entity.__dict__.get('options_defaults'):
        entity.options_defaults = {}
    entity.options_defaults.update(kwargs)


def using_options_handler(entity, *args, **kwargs):
    for kwarg in kwargs:
        if kwarg in valid_options:
            setattr(entity._descriptor, kwarg, kwargs[kwarg])
        else:
            raise Exception("'%s' is not a valid option for Elixir entities."
                            % kwarg)


def using_table_options_handler(entity, *args, **kwargs):
    entity._descriptor.table_args.extend(list(args))
    entity._descriptor.table_options.update(kwargs)


def using_mapper_options_handler(entity, *args, **kwargs):
    entity._descriptor.mapper_options.update(kwargs)


using_options_defaults = ClassMutator(using_options_defaults_handler)
using_options = ClassMutator(using_options_handler)
using_table_options = ClassMutator(using_table_options_handler)
using_mapper_options = ClassMutator(using_mapper_options_handler)
