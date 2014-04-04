import time

from couchpotato.core.logger import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent,fireEvent
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)

autoload = 'Charts'


class Charts(Plugin):

    update_in_progress = False

    def __init__(self):
        addApiView('charts.view', self.automationView)
        addEvent('app.load', self.setCrons)

    def setCrons(self):
        fireEvent('schedule.interval', 'charts.update_cache', self.updateViewCache, hours = self.conf('update_interval', default = 12))
        self.updateViewCache()


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
            self.setCache('charts_cached', charts, timeout = 2*3600*self.conf('update_interval', default = 12))
        except:
            log.error('Failed refreshing charts')

        self.update_in_progress = False

        return charts


config = [{
    'name': 'charts',
    'groups': [
        {
            'label': 'Charts',
            'description': 'Displays selected charts on the home page',
            'type': 'list',
            'name': 'charts_providers',
            'tab': 'display',
            'options': [
                {
                    'name': 'max_items',
                    'default': 10,
                    'type': 'int',
                    'description': 'Maximum number of items displayed from each chart.',
                },
                {
                    'name': 'update_interval',
                    'default': 12,
                    'type': 'int',
                    'advanced': True,
                    'description': '(hours)',
                },
            ],
        },
    ],
}]
