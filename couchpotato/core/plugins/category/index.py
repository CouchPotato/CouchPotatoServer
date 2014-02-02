from hashlib import md5
from CodernityDB.tree_index import TreeBasedIndex


class CategoryIndex(TreeBasedIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(CategoryIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'category':
            return md5(data['media_id']).hexdigest(), None
