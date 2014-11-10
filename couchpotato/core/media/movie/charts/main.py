import time

from couchpotato.core.logger import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent,fireEvent
from couchpotato.core.plugins.base import Plugin
import tmdb3

log = CPLog(__name__)


class Charts(Plugin):

    update_in_progress = False
    update_interval = 72 # hours

    def __init__(self):
        addApiView('charts.view', self.automationView)
        addEvent('app.load', self.setCrons)

    def setCrons(self):
        fireEvent('schedule.interval', 'charts.update_cache', self.updateViewCache, hours = self.update_interval)

    def automationView(self, force_update = False, **kwargs):

        if force_update:
            charts = self.updateViewCache()
        else:
            charts = self.getCache('charts_cached')
            if not charts:
                charts = self.updateViewCache()
        y=0
        for chart in charts:
            x=0
            for item in chart['list']:
                movie = tmdb3.Movie(item['imdb'])
                try:
                    charts[y]['list'][x]['plot']=movie.overview
                    charts[y]['list'][x]['titles'][0]=movie.title
                    charts[y]['list'][x]['images']['poster'][0]=charts[y]['list'][x]['images']['poster_original'][y][:charts[y]['list'][x]['images']['poster_original'][0].rfind('/')+1]+movie.posters[0].filename
                except:
                    x+=1
                    continue
                x+=1
            y+=1  
        return {
            'success': True,
            'count': len(charts),
            'charts': charts
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
