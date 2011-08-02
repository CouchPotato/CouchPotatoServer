from .main import ThePirateBay

def start():
    return ThePirateBay()

config = [{
    'name': 'thepiratebay',
    'groups': [
        {
            'tab': 'providers',
            'name': 'tpb',
            'label': 'The Pirate Bay',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                }
            ],
        },
    ],
}]
