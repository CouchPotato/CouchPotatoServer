from .main import Automation


def start():
    return Automation()

config = [{
    'name': 'automation',
    'order': 101,
    'groups': [
        {
            'tab': 'automation',
            'name': 'automation',
            'label': 'Minimal movie requirements',
            'options': [
                {
                    'name': 'year',
                    'default': 2011,
                    'type': 'int',
                },
                {
                    'name': 'votes',
                    'default': 1000,
                    'type': 'int',
                },
                {
                    'name': 'rating',
                    'default': 7.0,
                    'type': 'float',
                },
                {
                    'name': 'hour',
                    'advanced': True,
                    'default': 12,
                    'label': 'Check every',
                    'type': 'int',
                    'unit': 'hours',
                    'description': 'hours',
                },
                {
                    'name': 'required_genres',
                    'label': 'Required Genres',
                    'default': '',
                    'placeholder': 'Example: Action, Crime & Drama',
                    'description': ('Ignore movies that don\'t contain at least one set of genres.', 'Sets are separated by "," and each word within a set must be separated with "&"')
                },
                {
                    'name': 'ignored_genres',
                    'label': 'Ignored Genres',
                    'default': '',
                    'placeholder': 'Example: Horror, Comedy & Drama & Romance',
                    'description': 'Ignore movies that contain at least one set of genres. Sets work the same as above.'
                },
            ],
        },
    ],
}]
