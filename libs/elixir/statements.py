import sys

MUTATORS = '__elixir_mutators__'

class ClassMutator(object):
    '''
    DSL-style syntax

    A ``ClassMutator`` object represents a DSL term.
    '''

    def __init__(self, handler):
        '''
        Create a new ClassMutator, using the `handler` callable to process it
        when the time will come.
        '''
        self.handler = handler

    # called when a mutator (eg. "has_field(...)") is parsed
    def __call__(self, *args, **kwargs):
        # self in this case is the "generic" mutator (eg "has_field")

        # jam this mutator into the class's mutator list
        class_locals = sys._getframe(1).f_locals
        mutators = class_locals.setdefault(MUTATORS, [])
        mutators.append((self, args, kwargs))

    def process(self, entity, *args, **kwargs):
        '''
        Process one mutator. This version simply calls the handler callable,
        but another mutator (sub)class could do more processing.
        '''
        self.handler(entity, *args, **kwargs)


#TODO: move this to the super class (to be created here) of EntityMeta
def process_mutators(entity):
    '''
    Apply all mutators of the given entity. That is, loop over all mutators
    in the class's mutator list and process them.
    '''
    # we don't use getattr here to not inherit from the parent mutators
    # inadvertantly if the current entity hasn't defined any mutator.
    mutators = entity.__dict__.get(MUTATORS, [])
    for mutator, args, kwargs in mutators:
        mutator.process(entity, *args, **kwargs)

class Statement(ClassMutator):

    def process(self, entity, *args, **kwargs):
        builder = self.handler(entity, *args, **kwargs)
        entity._descriptor.builders.append(builder)

class PropertyStatement(ClassMutator):

    def process(self, entity, name, *args, **kwargs):
        prop = self.handler(*args, **kwargs)
        prop.attach(entity, name)

