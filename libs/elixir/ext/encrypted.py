'''
An encryption plugin for Elixir utilizing the excellent PyCrypto library, which
can be downloaded here: http://www.amk.ca/python/code/crypto

Values for columns that are specified to be encrypted will be transparently
encrypted and safely encoded for storage in a unicode column using the powerful
and secure Blowfish Cipher using a specified "secret" which can be passed into
the plugin at class declaration time.

Example usage:

.. sourcecode:: python

    from elixir import *
    from elixir.ext.encrypted import acts_as_encrypted

    class Person(Entity):
        name = Field(Unicode)
        password = Field(Unicode)
        ssn = Field(Unicode)
        acts_as_encrypted(for_fields=['password', 'ssn'],
                          with_secret='secret')

The above Person entity will automatically encrypt and decrypt the password and
ssn columns on save, update, and load.  Different secrets can be specified on
an entity by entity basis, for added security.

**Important note**: instance attributes are encrypted in-place. This means that
if one of the encrypted attributes of an instance is accessed after the
instance has been flushed to the database (and thus encrypted), the value for
that attribute will be crypted in the in-memory object in addition to the
database row.
'''

from Crypto.Cipher import Blowfish
from elixir.statements import Statement
from sqlalchemy.orm import MapperExtension, EXT_CONTINUE, EXT_STOP

try:
    from sqlalchemy.orm import EXT_PASS
    SA05orlater = False
except ImportError:
    SA05orlater = True

__all__ = ['acts_as_encrypted']
__doc_all__ = []


#
# encryption and decryption functions
#

def encrypt_value(value, secret):
    return Blowfish.new(secret, Blowfish.MODE_CFB) \
                   .encrypt(value).encode('string_escape')

def decrypt_value(value, secret):
    return Blowfish.new(secret, Blowfish.MODE_CFB) \
                   .decrypt(value.decode('string_escape'))


#
# acts_as_encrypted statement
#

class ActsAsEncrypted(object):

    def __init__(self, entity, for_fields=[], with_secret='abcdef'):

        def perform_encryption(instance, encrypt=True):
            encrypted = getattr(instance, '_elixir_encrypted', None)
            if encrypted is encrypt:
                # skipping encryption or decryption, as it is already done
                return
            else:
                # marking instance as already encrypted/decrypted
                instance._elixir_encrypted = encrypt

            if encrypt:
                func = encrypt_value
            else:
                func = decrypt_value

            for column_name in for_fields:
                current_value = getattr(instance, column_name)
                if current_value:
                    setattr(instance, column_name,
                            func(current_value, with_secret))

        def perform_decryption(instance):
            perform_encryption(instance, encrypt=False)

        class EncryptedMapperExtension(MapperExtension):

            def before_insert(self, mapper, connection, instance):
                perform_encryption(instance)
                return EXT_CONTINUE

            def before_update(self, mapper, connection, instance):
                perform_encryption(instance)
                return EXT_CONTINUE

            if SA05orlater:
                def reconstruct_instance(self, mapper, instance):
                    perform_decryption(instance)
                    # no special return value is required for
                    # reconstruct_instance, but you never know...
                    return EXT_CONTINUE
            else:
                def populate_instance(self, mapper, selectcontext, row,
                                      instance, *args, **kwargs):
                    mapper.populate_instance(selectcontext, instance, row,
                                             *args, **kwargs)
                    perform_decryption(instance)
                    # EXT_STOP because we already did populate the instance and
                    # the normal processing should not happen
                    return EXT_STOP

        # make sure that the entity's mapper has our mapper extension
        entity._descriptor.add_mapper_extension(EncryptedMapperExtension())


acts_as_encrypted = Statement(ActsAsEncrypted)

