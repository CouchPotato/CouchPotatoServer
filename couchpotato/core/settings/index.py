from CodernityDB.hash_index import UniqueHashIndex, HashIndex
from hashlib import md5


class PropertyIndex(HashIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(PropertyIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'property':
            return md5(data['identifier']).hexdigest(), None
