from CodernityDB.tree_index import TreeBasedIndex


class ProfileIndex(TreeBasedIndex):
    _version = 1

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'i'
        super(ProfileIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return key

    def make_key_value(self, data):
        if data.get('_t') == 'profile':
            return data.get('order', 99), None
