'''
Default entity collection implementation
'''
import sys
import re

from elixir.py23compat import rsplit

class BaseCollection(list):
    def __init__(self, entities=None):
        list.__init__(self)
        if entities is not None:
            self.extend(entities)

    def extend(self, entities):
        for e in entities:
            self.append(e)

    def clear(self):
        del self[:]

    def resolve_absolute(self, key, full_path, entity=None, root=None):
        if root is None:
            root = entity._descriptor.resolve_root
        if root:
            full_path = '%s.%s' % (root, full_path)
        module_path, classname = rsplit(full_path, '.', 1)
        module = sys.modules[module_path]
        res = getattr(module, classname, None)
        if res is None:
            if entity is not None:
                raise Exception("Couldn't resolve target '%s' <%s> in '%s'!"
                                % (key, full_path, entity.__name__))
            else:
                raise Exception("Couldn't resolve target '%s' <%s>!"
                                % (key, full_path))
        return res

    def __getattr__(self, key):
        return self.resolve(key)

# default entity collection
class GlobalEntityCollection(BaseCollection):
    def __init__(self, entities=None):
        # _entities is a dict of entities keyed on their name.
        self._entities = {}
        super(GlobalEntityCollection, self).__init__(entities)

    def append(self, entity):
        '''
        Add an entity to the collection.
        '''
        super(EntityCollection, self).append(entity)

        existing_entities = self._entities.setdefault(entity.__name__, [])
        existing_entities.append(entity)

    def resolve(self, key, entity=None):
        '''
        Resolve a key to an Entity. The optional `entity` argument is the
        "source" entity when resolving relationship targets.
        '''
        # Do we have a fully qualified entity name?
        if '.' in key:
            return self.resolve_absolute(key, key, entity)
        else:
            # Otherwise we look in the entities of this collection
            res = self._entities.get(key, None)
            if res is None:
                if entity:
                    raise Exception("Couldn't resolve target '%s' in '%s'"
                                    % (key, entity.__name__))
                else:
                    raise Exception("This collection does not contain any "
                                    "entity corresponding to the key '%s'!"
                                    % key)
            elif len(res) > 1:
                raise Exception("'%s' resolves to several entities, you should"
                                " use the full path (including the full module"
                                " name) to that entity." % key)
            else:
                return res[0]

    def clear(self):
        self._entities = {}
        super(GlobalEntityCollection, self).clear()

# backward compatible name
EntityCollection = GlobalEntityCollection

_leading_dots = re.compile('^([.]*).*$')

class RelativeEntityCollection(BaseCollection):
    # the entity=None does not make any sense with a relative entity collection
    def resolve(self, key, entity):
        '''
        Resolve a key to an Entity. The optional `entity` argument is the
        "source" entity when resolving relationship targets.
        '''
        full_path = key

        if '.' not in key or key.startswith('.'):
            # relative target

            # any leading dot is stripped and with each dot removed,
            # the entity_module is stripped of one more chunk (starting with
            # the last one).
            num_dots = _leading_dots.match(full_path).end(1)
            full_path = full_path[num_dots:]
            chunks = entity.__module__.split('.')
            chunkstokeep = len(chunks) - num_dots
            if chunkstokeep < 0:
                raise Exception("Couldn't resolve relative target "
                    "'%s' relative to '%s'" % (key, entity.__module__))
            entity_module = '.'.join(chunks[:chunkstokeep])

            if entity_module and entity_module is not '__main__':
                full_path = '%s.%s' % (entity_module, full_path)

            root = ''
        else:
            root = None
        return self.resolve_absolute(key, full_path, entity, root=root)

    def __getattr__(self, key):
        raise NotImplementedError

