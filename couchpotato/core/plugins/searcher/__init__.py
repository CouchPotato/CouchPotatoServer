from .main import Searcher
import random

def start():
    return Searcher()

config = [{
    'name': 'searcher',
    'order': 20,
    'groups': [
        {
            'tab': 'searcher',
            'name': 'searcher',
            'label': 'Search',
            'description': 'Options for the searchers',
            'options': [
                {
                    'name': 'preferred_words',
                    'label': 'Preferred words',
                    'default': '',
                    'description': 'These words will give the releases a higher score.'
                },
                {
                    'name': 'required_words',
                    'label': 'Required words',
                    'default': '',
                    'description': 'Ignore releases that don\'t contain at least one of these words.'
                },
                {
                    'name': 'ignored_words',
                    'label': 'Ignored words',
                    'default': 'german, dutch, french, truefrench, danish, swedish, spanish, italian, korean, dubbed, swesub, korsub',
                },
                {
                    'name': 'preferred_method',
                    'label': 'Preferred download method',
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('usenet & torrents', 'both'), ('usenet', 'usenet'), ('torrents', 'torrents')],
                },
            ],
        }, {
            'tab': 'searcher',
            'name': 'cronjob',
            'label': 'Cronjob',
            'advanced': True,
            'description': 'Cron settings for the searcher see: <a href="http://packages.python.org/APScheduler/cronschedule.html">APScheduler</a> for details.',
            'options': [
                {
                    'name': 'cron_day',
                    'label': 'Day',
                    'advanced': True,
                    'default': '*',
                    'type': 'string',
                    'description': '<strong>*</strong>: Every day, <strong>*/2</strong>: Every 2 days, <strong>1</strong>: Every first of the month.',
                },
                {
                    'name': 'cron_hour',
                    'label': 'Hour',
                    'advanced': True,
                    'default': random.randint(0, 23),
                    'type': 'string',
                    'description': '<strong>*</strong>: Every hour, <strong>*/8</strong>: Every 8 hours, <strong>3</strong>: At 3, midnight.',
                },
                {
                    'name': 'cron_minute',
                    'label': 'Minute',
                    'advanced': True,
                    'default': random.randint(0, 59),
                    'type': 'string',
                    'description': "Just keep it random, so the providers don't get DDOSed by every CP user on a 'full' hour."
                },
            ],
        },
    ],
}, {
    'name': 'nzb',
    'groups': [
        {
            'tab': 'searcher',
            'name': 'nzb',
            'label': 'NZB',
            'wizard': True,
            'options': [
                {
                    'name': 'retention',
                    'default': 1000,
                    'type': 'int',
                    'unit': 'days'
                },
            ],
        },
    ],
}]
