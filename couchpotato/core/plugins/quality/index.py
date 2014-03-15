from hashlib import md5

from CodernityDB.hash_index import HashIndex


class QualityIndex(HashIndex):
    _version = 1

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(QualityIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'quality' and data.get('identifier'):
            return md5(data.get('identifier')).hexdigest(), None
