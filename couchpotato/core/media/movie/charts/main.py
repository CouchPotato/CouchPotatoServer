import time
from CodernityDB.database import RecordNotFound
from couchpotato import Env, get_db
from couchpotato.core.helpers.variable import getTitle, splitString

from couchpotato.core.logger import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent,fireEvent
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)


class Charts(Plugin):

    update_in_progress = False
    update_interval = 72 # hours

    def __init__(self):
        addApiView('charts.view', self.automationView)
        addApiView('charts.ignore', self.ignoreView)

    def automationView(self, force_update = False, **kwargs):

        db = get_db()

        if force_update:
            charts = self.updateViewCache()
        else:
            charts = self.getCache('charts_cached')
            if not charts:
                charts = self.updateViewCache()

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
                poster = media.get('images', {}).get('poster', [])
                cached_poster = fireEvent('file.download', url = poster[0], single = True) if len(poster) > 0 else False
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

    def updateViewCache(self):

        if self.update_in_progress:
            while self.update_in_progress:
                time.sleep(1)
            catched_charts = self.getCache('charts_cached')
            if catched_charts:
                return catched_charts

        charts = []
        try:
            self.update_in_progress = True
            charts = fireEvent('automation.get_chart_list', merge = True)
            for chart in charts:
                chart['hide_wanted'] = self.conf('hide_wanted')
                chart['hide_library'] = self.conf('hide_library')

            self.setCache('charts_cached', charts, timeout = self.update_interval * 3600)
        except:
            log.error('Failed refreshing charts')

        self.update_in_progress = False

        return charts

    def ignoreView(self, imdb = None, **kwargs):

        ignored = splitString(Env.prop('charts_ignore', default = ''))

        if imdb:
            ignored.append(imdb)
            Env.prop('charts_ignore', ','.join(set(ignored)))

        return {
            'result': True
        }
