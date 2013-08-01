from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie, Category

log = CPLog(__name__)


class CategoryPlugin(Plugin):

    to_dict = {'destination': {}}

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
            temp.append(category.to_dict(self.to_dict))

        db.expire_all()
        return temp

    def save(self, **kwargs):

        db = get_session()

        c = db.query(Category).filter_by(id = kwargs.get('id')).first()
        if not c:
            c = Category()
            db.add(c)

        c.order = kwargs.get('order', c.order if c.order else 0)
        c.label = toUnicode(kwargs.get('label'))
        c.path = toUnicode(kwargs.get('path'))
        c.ignored = toUnicode(kwargs.get('ignored'))
        c.preferred = toUnicode(kwargs.get('preferred'))
        c.required = toUnicode(kwargs.get('required'))

        db.commit()

        category_dict = c.to_dict(self.to_dict)

        return {
            'success': True,
            'category': category_dict
        }

    def saveOrder(self, **kwargs):

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

    def delete(self, id = None, **kwargs):

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
        except Exception, e:
            message = log.error('Failed deleting category: %s', e)

        db.expire_all()
        return {
            'success': success,
            'message': message
        }

    def removeFromMovie(self, category_id):

        db = get_session()
        movies = db.query(Movie).filter(Movie.category_id == category_id).all()

        if len(movies) > 0:
            for movie in movies:
                movie.category_id = None
                db.commit()
