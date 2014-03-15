import traceback

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from .index import CategoryIndex, CategoryMediaIndex


log = CPLog(__name__)


class CategoryPlugin(Plugin):

    _database = {
        'category': CategoryIndex,
        'category_media': CategoryMediaIndex,
    }

    def __init__(self):
        addApiView('category.save', self.save)
        addApiView('category.save_order', self.saveOrder)
        addApiView('category.delete', self.delete)
        addApiView('category.list', self.allView, docs = {
            'desc': 'List all available categories',
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, categories
}"""}
        })

        addEvent('category.all', self.all)

    def allView(self, **kwargs):

        return {
            'success': True,
            'categories': self.all()
        }

    def all(self):

        db = get_db()
        categories = db.all('category', with_doc = True)

        return [x['doc'] for x in categories]

    def save(self, **kwargs):

        try:
            db = get_db()

            category = {
                '_t': 'category',
                'order': kwargs.get('order', 999),
                'label': toUnicode(kwargs.get('label', '')),
                'ignored': toUnicode(kwargs.get('ignored', '')),
                'preferred': toUnicode(kwargs.get('preferred', '')),
                'required': toUnicode(kwargs.get('required', '')),
                'destination': toUnicode(kwargs.get('destination', '')),
            }

            try:
                c = db.get('id', kwargs.get('id'))
                category['order'] = c.get('order', category['order'])
                c.update(category)

                db.update(c)
            except:
                c = db.insert(category)
                c.update(category)

            return {
                'success': True,
                'category': c
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False,
            'category': None
        }

    def saveOrder(self, **kwargs):

        try:
            db = get_db()

            order = 0
            for category_id in kwargs.get('ids', []):
                c = db.get('id', category_id)
                c['order'] = order
                db.update(c)

                order += 1

            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }

    def delete(self, id = None, **kwargs):

        try:
            db = get_db()

            success = False
            message = ''
            try:
                c = db.get('id', id)
                db.delete(c)

                # Force defaults on all empty category movies
                self.removeFromMovie(id)

                success = True
            except:
                message = log.error('Failed deleting category: %s', traceback.format_exc())

            return {
                'success': success,
                'message': message
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }

    def removeFromMovie(self, category_id):

        try:
            db = get_db()
            movies = [x['doc'] for x in db.get_many('category_media', category_id, with_doc = True)]

            if len(movies) > 0:
                for movie in movies:
                    movie['category_id'] = None
                    db.update(movie)
        except:
            log.error('Failed: %s', traceback.format_exc())
