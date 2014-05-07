import time

from couchpotato import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent,fireEvent
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)


class Charts(Plugin):

    update_in_progress = False

    def __init__(self):
        addApiView('charts.view', self.automationView)
        addEvent('app.load', self.setCrons)

    def setCrons(self):
        fireEvent('schedule.interval', 'charts.update_cache', self.updateViewCache, hours = self.conf('update_interval', default = 12))

    def automationView(self, force_update = False, **kwargs):

        if force_update:
            charts = self.updateViewCache()
        else:
            charts = self.getCache('charts_cached')
            if not charts:
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
            for chart in charts:
                chart['hide_wanted'] = self.conf('hide_wanted')
                chart['hide_library'] = self.conf('hide_library')
            self.setCache('charts_cached', charts, timeout = 7200 * tryInt(self.conf('update_interval', default = 12)))
        except:
            log.error('Failed refreshing charts')

        self.update_in_progress = False

        return charts
