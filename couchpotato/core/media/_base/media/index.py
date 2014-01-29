from CodernityDB.hash_index import HashIndex
from CodernityDB.tree_index import MultiTreeBasedIndex


class MediaIMDBIndex(HashIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'I'
        super(MediaIMDBIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return int(key.strip('t'))

    def make_key_value(self, data):
        if data.get('type') == 'media' and data.get('identifier'):
            return int(data['identifier'].strip('t')), None


class MediaStatusIndex(HashIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 's'
        super(MediaStatusIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return int(key.strip('t'))

    def make_key_value(self, data):
        if data.get('type') == 'media' and data.get('identifier'):
            return int(data['identifier'].strip('t')), None


class TitleIndex(MultiTreeBasedIndex):

    custom_header = """from CodernityDB.tree_index import MultiTreeBasedIndex
from itertools import izip"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(TitleIndex, self).__init__(*args, **kwargs)
        self.__l = kwargs.get('w_len', 2)

    def make_key_value(self, data):

        if data.get('type') == 'title' and len(data.get('title', '')) > 0:

            out = set()
            title = data.get('title').lower()
            l = self.__l
            max_l = len(title)
            for x in xrange(l - 1, max_l):
                m = (title, )
                for y in xrange(0, x):
                    m += (title[y + 1:],)
                out.update(set(''.join(x).rjust(32, '_').lower() for x in izip(*m)))  #ignore import error

            return out, {'media_id': data.get('media_id')}

    def make_key(self, key):
        return key.rjust(32, '_').lower()
