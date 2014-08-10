import traceback

from couchpotato import fireEvent, get_db, tryInt, CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import splitString, mergeDicts
from couchpotato.core.media._base.quality.index import QualityIndex
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Quality(Plugin):
    _database = {
        'quality': QualityIndex
    }

    def __init__(self):
        addEvent('quality.single', self.single)

        addApiView('quality.list', self.allView, docs = {
            'desc': 'List all available qualities',
            'params': {
                'type': {'type': 'string', 'desc': 'Media type to filter on.'},
            },
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, qualities
}"""}
        })

        addApiView('quality.size.save', self.saveSize)

    def single(self, identifier = '', types = None):
        db = get_db()
        quality = db.get('quality', identifier, with_doc = True)['doc']

        if quality:
            return mergeDicts(
                fireEvent(
                    'quality.get',
                    quality['identifier'],
                    types = types,
                    single = True
                ),
                quality
            )

        return {}

    def allView(self, **kwargs):

        return {
            'success': True,
            'list': fireEvent(
                'quality.all',
                types = splitString(kwargs.get('type')),
                merge = True
            )
        }

    def saveSize(self, **kwargs):

        try:
            db = get_db()
            quality = db.get('quality', kwargs.get('identifier'), with_doc = True)

            if quality:
                quality['doc'][kwargs.get('value_type')] = tryInt(kwargs.get('value'))
                db.update(quality['doc'])

            fireEvent('quality.reset_cache')

            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }
