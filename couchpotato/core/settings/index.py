from CodernityDB.hash_index import UniqueHashIndex, HashIndex
from hashlib import md5


class PropertyIndex(HashIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '16s'
        super(PropertyIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).digest()

    def make_key_value(self, data):
        if data.get('type') == 'property':
            return md5(data['identifier']).digest(), None
