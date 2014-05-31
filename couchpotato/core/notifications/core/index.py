from CodernityDB.tree_index import TreeBasedIndex


class NotificationIndex(TreeBasedIndex):
    _version = 1

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
import time"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'I'
        super(NotificationIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return key

    def make_key_value(self, data):
        if data.get('_t') == 'notification':
            return data.get('time'), None


class NotificationUnreadIndex(TreeBasedIndex):
    _version = 1

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
import time"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'I'
        super(NotificationUnreadIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return key

    def make_key_value(self, data):
        if data.get('_t') == 'notification' and not data.get('read'):
            return data.get('time'), None
