from itertools import izip
from string import ascii_letters
from CodernityDB.hash_index import HashIndex
from CodernityDB.tree_index import MultiTreeBasedIndex, TreeBasedIndex
from hashlib import md5
from couchpotato.core.helpers.encoding import toUnicode, simplifyString


class MediaIMDBIndex(HashIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = 'I'
        super(MediaIMDBIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return int(key.strip('t'))

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('identifier'):
            return int(data['identifier'].strip('t')), None

    def run_to_dict(self, db, media_id, dict = None):
        if not dict: dict = {}

        return db.get('id', media_id)

    def run_with_status(self, db, status = [], with_doc = True):

        status = list(status if isinstance(status, (list, tuple)) else [status])

        for s in status:
            for ms in db.get_many('media_status', s, with_doc = with_doc):
                yield ms['doc'] if with_doc else ms


class MediaStatusIndex(TreeBasedIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(MediaStatusIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('status'):
            return md5(data.get('status')).hexdigest(), None


class MediaTypeIndex(TreeBasedIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(MediaTypeIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('type'):
            return md5(data.get('type')).hexdigest(), None


class TitleSearchIndex(MultiTreeBasedIndex):

    custom_header = """from CodernityDB.tree_index import MultiTreeBasedIndex
from itertools import izip
from couchpotato.core.helpers.encoding import simplifyString"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(TitleSearchIndex, self).__init__(*args, **kwargs)
        self.__l = kwargs.get('w_len', 2)

    def make_key_value(self, data):

        if data.get('_t') == 'media' and len(data.get('title', '')) > 0:

            out = set()
            title = str(simplifyString(data.get('title').lower()))
            l = self.__l
            max_l = len(title)
            for x in xrange(l - 1, max_l):
                m = (title, )
                for y in xrange(0, x):
                    m += (title[y + 1:],)
                out.update(set(''.join(x).rjust(32, '_').lower() for x in izip(*m)))

            return out, None

    def make_key(self, key):
        return key.rjust(32, '_').lower()


class TitleIndex(TreeBasedIndex):

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
from string import ascii_letters
from couchpotato.core.helpers.encoding import toUnicode, simplifyString"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(TitleIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return self.simplify(key)

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('title') is not None:
            return self.simplify(data['title']), None

    def simplify(self, title):

        title = toUnicode(title)

        nr_prefix = '' if title[0] in ascii_letters else '#'
        title = simplifyString(title)

        for prefix in ['the ']:
            if prefix == title[:len(prefix)]:
                title = title[len(prefix):]
                break

        return str(nr_prefix + title).ljust(32, '_')[:32]


class StartsWithIndex(TreeBasedIndex):

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
from string import ascii_letters
from couchpotato.core.helpers.encoding import toUnicode, simplifyString"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '1s'
        super(StartsWithIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return self.first(key)

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('title') is not None:
            return self.first(data['title']), None

    def first(self, title):
        title = toUnicode(title)
        title = simplifyString(title)

        for prefix in ['the ']:
            if prefix == title[:len(prefix)]:
                title = title[len(prefix):]
                break

        return str(title[0] if title[0] in ascii_letters else '#').lower()
