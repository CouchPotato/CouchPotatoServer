from .main import Boxcar

def start():
    return Boxcar()

config = [{
    'name': 'boxcar',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'boxcar',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'email',
                    'description': 'Your Boxcar registration emailaddress.'
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
