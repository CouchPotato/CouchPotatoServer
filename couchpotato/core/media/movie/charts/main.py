from CodernityDB.database import RecordNotFound
from couchpotato import Env, get_db
from couchpotato.core.helpers.variable import getTitle, splitString

from couchpotato.core.logger import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)


class Charts(Plugin):

    def __init__(self):
        addApiView('charts.view', self.automationView)
        addApiView('charts.ignore', self.ignoreView)

    def automationView(self, force_update = False, **kwargs):

        db = get_db()

        charts = fireEvent('automation.get_chart_list', merge = True)
        ignored = splitString(Env.prop('charts_ignore', default = ''))

        # Create a list the movie/list.js can use
        for chart in charts:
            medias = []
            for media in chart.get('list', []):

                identifier = media.get('imdb')
                if identifier in ignored:
                    continue

                try:
                    try:
                        in_library = db.get('media', 'imdb-%s' % identifier)
                        if in_library:
                            continue
                    except RecordNotFound:
                        pass
                except:
                    pass

                # Cache poster
                posters = media.get('images', {}).get('poster', [])
                poster = [x for x in posters if 'tmdb' in x]
                posters = poster if len(poster) > 0 else posters

                cached_poster = fireEvent('file.download', url = posters[0], single = True) if len(posters) > 0 else False
                files = {'image_poster': [cached_poster] } if cached_poster else {}

                medias.append({
                    'status': 'chart',
                    'title': getTitle(media),
                    'type': 'movie',
                    'info': media,
                    'files': files,
                    'identifiers': {
                        'imdb': identifier
                    }
                })

            chart['list'] = medias

        return {
            'success': True,
            'count': len(charts),
            'charts': charts,
            'ignored': ignored,
        }

    def ignoreView(self, imdb = None, **kwargs):

        ignored = splitString(Env.prop('charts_ignore', default = ''))

        if imdb:
            ignored.append(imdb)
            Env.prop('charts_ignore', ','.join(set(ignored)))

        return {
            'result': True
        }
