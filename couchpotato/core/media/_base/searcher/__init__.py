from .main import Searcher


def autoload():
    return Searcher()

config = [{
    'name': 'searcher',
    'order': 20,
    'groups': [
        {
            'tab': 'searcher',
            'name': 'searcher',
            'label': 'Basics',
            'description': 'General search options',
            'options': [
                {
                    'name': 'preferred_method',
                    'label': 'First search',
                    'description': 'Which of the methods do you prefer',
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('usenet & torrents', 'both'), ('usenet', 'nzb'), ('torrents', 'torrent')],
                },
            ],
        }, {
            'tab': 'searcher',
            'subtab': 'category',
            'subtab_label': 'Categories',
            'name': 'filter',
            'label': 'Global filters',
            'description': 'Prefer, ignore & required words in release names',
            'options': [
                {
                    'name': 'preferred_words',
                    'label': 'Preferred',
                    'default': '',
                    'placeholder': 'Example: CtrlHD, Amiable, Wiki',
                    'description': 'Words that give the releases a higher score.'
                },
                {
                    'name': 'required_words',
                    'label': 'Required',
                    'default': '',
                    'placeholder': 'Example: DTS, AC3 & English',
                    'description': 'Release should contain at least one set of words. Sets are separated by "," and each word within a set must be separated with "&"'
                },
                {
                    'name': 'ignored_words',
                    'label': 'Ignored',
                    'default': 'german, dutch, french, truefrench, danish, swedish, spanish, italian, korean, dubbed, swesub, korsub, dksubs, vain, HC',
                    'description': 'Ignores releases that match any of these sets. (Works like explained above)'
                },
            ],
        },
    ],
}, {
    'name': 'nzb',
    'groups': [
        {
            'tab': 'searcher',
            'name': 'searcher',
            'label': 'NZB',
            'wizard': True,
            'options': [
                {
                    'name': 'retention',
                    'label': 'Usenet Retention',
                    'default': 1500,
                    'type': 'int',
                    'unit': 'days'
                },
            ],
        },
    ],
}, {
    'name': 'torrent',
    'groups': [
        {
            'tab': 'searcher',
            'name': 'searcher',
            'wizard': True,
            'options': [
                {
                    'name': 'minimum_seeders',
                    'advanced': True,
                    'label': 'Minimum seeders',
                    'description': 'Ignore torrents with seeders below this number',
                    'default': 1,
                    'type': 'int',
                    'unit': 'seeders'
                },
            ],
        },
    ],
}]
