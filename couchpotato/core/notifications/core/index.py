import time
from CodernityDB.tree_index import TreeBasedIndex


class NotificationIndex(TreeBasedIndex):

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
import time"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'I'
        super(NotificationIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return key

    def make_key_value(self, data):
        if data.get('_t') == 'notification':
            added = data.get('added', time.time())
            data['added'] = added

            return added, None


class NotificationUnreadIndex(TreeBasedIndex):

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
import time"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'I'
        super(NotificationUnreadIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return key

    def make_key_value(self, data):
        if data.get('_t') == 'notification' and not data.get('read'):
            added = data.get('added', time.time())
            data['added'] = added

            return added, None
