from CodernityDB.tree_index import TreeBasedIndex


class CategoryIndex(TreeBasedIndex):
    _version = 1

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'i'
        super(CategoryIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return key

    def make_key_value(self, data):
        if data.get('_t') == 'category':
            return data.get('order', -99), None


class CategoryMediaIndex(TreeBasedIndex):
    _version = 1

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(CategoryMediaIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return str(key)

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('category_id'):
            return str(data.get('category_id')), None
