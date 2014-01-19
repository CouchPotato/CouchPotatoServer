from .main import Newznab


def start():
    return Newznab()

config = [{
    'name': 'newznab',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'newznab',
            'order': 10,
            'description': 'Enable <a href="http://newznab.com/" target="_blank">NewzNab</a> such as <a href="https://nzb.su" target="_blank">NZB.su</a>, \
                <a href="https://nzbs.org" target="_blank">NZBs.org</a>, <a href="http://dognzb.cr/" target="_blank">DOGnzb.cr</a>, \
                <a href="https://github.com/spotweb/spotweb" target="_blank">Spotweb</a>, <a href="https://nzbgeek.info/" target="_blank">NZBGeek</a>, \
                <a href="https://smackdownonyou.com" target="_blank">SmackDown</a>, <a href="https://www.nzbfinder.ws" target="_blank">NZBFinder</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
                },
                {
                    'name': 'use',
                    'default': '0,0,0,0,0,0'
                },
                {
                    'name': 'host',
                    'default': 'nzb.su,dognzb.cr,nzbs.org,https://index.nzbgeek.info, https://smackdownonyou.com, https://www.nzbfinder.ws',
                    'description': 'The hostname of your newznab provider',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': '0,0,0,0,0,0',
                    'description': 'Starting score for each release found via this provider.',
                },
                {
                    'name': 'custom_tag',
                    'advanced': True,
                    'label': 'Custom tag',
                    'default': ',,,,,',
                    'description': 'Add custom tags, for example add rls=1 to get only scene releases from nzbs.org',
                },
                {
                    'name': 'api_key',
                    'default': ',,,,,',
                    'label': 'Api Key',
                    'description': 'Can be found on your profile page',
                    'type': 'combined',
                    'combine': ['use', 'host', 'api_key', 'extra_score', 'custom_tag'],
                },
            ],
        },
    ],
}]
