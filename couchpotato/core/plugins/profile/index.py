from CodernityDB.hash_index import HashIndex
from hashlib import md5


class ProfileIndex(HashIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '16s'
        super(ProfileIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).digest()

    def make_key_value(self, data):
        if data.get('type') == 'profile' and data.get('identifier'):
            return md5(data.get('identifier')).digest(), None
