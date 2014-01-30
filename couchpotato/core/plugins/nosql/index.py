from hashlib import md5
from CodernityDB.tree_index import TreeBasedIndex, MultiTreeBasedIndex


class NameIndex(TreeBasedIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '16s'
        super(NameIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return key

    def make_key_value(self, data):
        if data.get('type') == 'media' and data.get('title') is not None:
            return data.get('title'), None

