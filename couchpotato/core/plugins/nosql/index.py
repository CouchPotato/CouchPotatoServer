from hashlib import md5
from CodernityDB.tree_index import TreeBasedIndex


class ReleaseIndex(TreeBasedIndex):

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '16s'
        super(ReleaseIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).digest()

    def make_key_value(self, data):
        if data.get('type') == 'release':
            return md5(data['media_id']).digest(), None

    def run_for_media(self, db, media_id):
        for release in db.get_many('release', media_id, with_doc=True):
            yield release['doc']
