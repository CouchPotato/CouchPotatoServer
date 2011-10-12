from .main import X264

def start():
    return X264()

config = [{
    'name': 'x264',
    'groups': [
        {
            'tab': 'providers',
            'name': '#alt.binaries.hdtv.x264',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
