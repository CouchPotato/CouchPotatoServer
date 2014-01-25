import traceback
from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media, Category

log = CPLog(__name__)


class CategoryPlugin(Plugin):

    def __init__(self):
        addEvent('category.all', self.all)

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

    def allView(self, **kwargs):

        return {
            'success': True,
            'list': self.all()
        }

    def all(self):

        db = get_session()
        categories = db.query(Category).all()

        temp = []
        for category in categories:
            temp.append(category.to_dict())

        return temp

    def save(self, **kwargs):

        try:
            db = get_session()

            c = db.query(Category).filter_by(id = kwargs.get('id')).first()
            if not c:
                c = Category()
                db.add(c)

            c.order = kwargs.get('order', c.order if c.order else 0)
            c.label = toUnicode(kwargs.get('label', ''))
            c.ignored = toUnicode(kwargs.get('ignored', ''))
            c.preferred = toUnicode(kwargs.get('preferred', ''))
            c.required = toUnicode(kwargs.get('required', ''))
            c.destination = toUnicode(kwargs.get('destination', ''))

            db.commit()

            category_dict = c.to_dict()

            return {
                'success': True,
                'category': category_dict
            }
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

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

            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

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

            return {
                'success': success,
                'message': message
            }
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

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
            db.close()
