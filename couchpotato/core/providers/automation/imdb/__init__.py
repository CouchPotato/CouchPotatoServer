from .main import IMDB

def start():
    return IMDB()

config = [{
    'name': 'imdb',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'imdb_automation_watchlist',
            'label': 'IMDB',
            'description': 'From any <strong>public</strong> IMDB watchlists. Url should be the CSV link.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                },
                {
                    'name': 'automation_urls',
                    'label': 'url',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                },
            ],
        },
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'imdb_automation_charts',
            'label': 'IMDB',
            'description': 'Import movies from IMDB Charts',
            'options': [
                {
                    'name': 'automation_providers_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_charts_theater',
                    'type': 'bool',
                    'label': 'In Theaters',
                    'description': 'New Movies <a href="http://www.imdb.com/movies-in-theaters/">In-Theaters</a> chart',
                    'default': True,
                },
                {
                    'name': 'automation_charts_top250',
                    'type': 'bool',
                    'label': 'TOP 250',
                    'description': 'IMDB <a href="http://www.imdb.com/chart/top/">TOP 250</a> chart',
                    'default': True,
                },
                {
                    'name': 'automation_charts_boxoffice',
                    'type': 'bool',
                    'label': 'Box office TOP 10',
                    'description': 'IMDB Box office <a href="http://www.imdb.com/chart/">TOP 10</a> chart',
                    'default': True,
                },
            ],
        },
        {
            'tab': 'display',
            'list': 'charts_providers',
            'name': 'imdb_charts_display',
            'label': 'IMDB',
            'description': 'Display movies from IMDB Charts',
            'options': [
                {
                    'name': 'chart_display_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'chart_display_theater',
                    'type': 'bool',
                    'label': 'In Theaters',
                    'description': 'New Movies <a href="http://www.imdb.com/movies-in-theaters/">In-Theaters</a> chart',
                    'default': False,
                },
                {
                    'name': 'chart_display_top250',
                    'type': 'bool',
                    'label': 'TOP 250',
                    'description': 'IMDB <a href="http://www.imdb.com/chart/top/">TOP 250</a> chart',
                    'default': False,
                },
                {
                    'name': 'chart_display_boxoffice',
                    'type': 'bool',
                    'label': 'Box office TOP 10',
                    'description': 'IMDB Box office <a href="http://www.imdb.com/chart/">TOP 10</a> chart',
                    'default': True,
                },
            ],
        },
    ],
}]
