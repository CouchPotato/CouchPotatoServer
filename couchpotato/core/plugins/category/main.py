import traceback
from couchpotato import get_session, get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from .index import CategoryIndex
from couchpotato.core.settings.model import Media, Category

log = CPLog(__name__)


class CategoryPlugin(Plugin):

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
        addEvent('database.setup', self.databaseSetup)

    def databaseSetup(self):

        db = get_db()

        # Release media_id index
        try:
            db.add_index(CategoryIndex(db.path, 'category'))
        except:
            log.debug('Index already exists')
            db.edit_index(CategoryIndex(db.path, 'category'))

    def allView(self, **kwargs):

        return {
            'success': True,
            'list': self.all()
        }

    def all(self):

        db = get_db()
        categories = db.all('category', with_doc = True)

        temp = []
        for category in categories:
            temp.append(category['doc'])

        return temp

    def save(self, **kwargs):

        try:
            db = get_db()

            category = {
                'order': kwargs.get('order', 0),
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
            db = get_session()

            order = 0
            for category_id in kwargs.get('ids', []):
                c = db.query(Category).filter_by(id = category_id).first()
                c.order = order

                order += 1

            db.commit()

            pass  #db.close()
            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            pass  #db.close()

        return {
            'success': False
        }

    def delete(self, id = None, **kwargs):

        try:
            db = get_session()

            success = False
            message = ''
            try:
                c = db.query(Category).filter_by(id = id).first()
                db.delete(c)
                db.commit()

                # Force defaults on all empty category movies
                self.removeFromMovie(id)

                success = True
            except Exception as e:
                message = log.error('Failed deleting category: %s', e)

            pass  #db.close()
            return {
                'success': success,
                'message': message
            }
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            pass  #db.close()

        return {
            'success': False
        }

    def removeFromMovie(self, category_id):

        try:
            db = get_session()
            movies = db.query(Media).filter(Media.category_id == category_id).all()

            if len(movies) > 0:
                for movie in movies:
                    movie.category_id = None
                    db.commit()
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            pass  #db.close()
