import time
from couchpotato.api import addApiView
from couchpotato.core.logger import CPLog
from couchpotato.core.event import addEvent,fireEvent
from couchpotato.core.plugins.base import Plugin
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import or_

log = CPLog(__name__)


class Charts(Plugin):

    update_in_progress = False

    def __init__(self):
        addApiView('charts.view', self.automationView)
        addEvent('app.load', self.setCrons)

    def setCrons(self):
        fireEvent('schedule.interval', 'charts.update_cache', self.updateViewCache, hours = self.conf('update_interval', default = 12))
        self.updateViewCache()


    def automationView(self):

        cached_charts = self.getCache('charts_cached')

        if cached_charts:
            charts = cached_charts
        else:
            charts = self.updateViewCache()

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

        try:
            self.update_in_progress = True
            charts = fireEvent('automation.get_chart_list', merge = True)
            self.setCache('charts_cached', charts, timeout = 86400) # Cache for 24 hours
        except:
            log.error('Failed at refreshing charts')

        self.update_in_progress = False

        return charts

