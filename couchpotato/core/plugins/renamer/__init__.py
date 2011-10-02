from couchpotato.core.plugins.renamer.main import Renamer

def start():
    return Renamer()

config = [{
    'name': 'renamer',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'renamer',
            'label': 'Folders',
            'description': 'Move and rename your downloaded movies to your movie directory.',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'from',
                    'type': 'directory',
                    'description': 'Folder where the movies are downloaded to.',
                },
                {
                    'name': 'to',
                    'type': 'directory',
                    'description': 'Folder where the movies will be moved to.',
                },
                {
                    'name': 'folder_name',
                    'label': 'Folder naming',
                    'description': 'Name of the folder',
                    'default': '<namethe> (<year>)',
                },
                {
                    'name': 'file_name',
                    'label': 'File naming',
                    'description': 'Name of the file',
                    'default': '<thename><cd>.<ext>',
                },
                {
                    'advanced': True,
                    'name': 'separator',
                    'label': 'Separator',
                    'description': 'Replace all the spaces with a character. Example: ".", "-". Leave empty to use spaces.',
                },
                {
                    'advanced': True,
                    'name': 'run_every',
                    'label': 'Run every',
                    'default': 1,
                    'type': 'int',
                    'unit': 'min(s)',
                    'description': 'Search for new movies inside the folder every X minutes.',
                },
            ],
        }, {
            'tab': 'renamer',
            'name': 'meta_renamer',
            'label': 'Advanced renaming',
            'description': 'Meta data file renaming. Use &lt;filename&gt; to use the above "File naming" settings, without the file extention.',
            'advanced': True,
            'options': [
                {
                    'name': 'rename_nfo',
                    'label': 'Rename .NFO',
                    'description': 'Rename original .nfo file',
                    'type': 'bool',
                    'default': True,
                },
                {
                    'name': 'nfo_name',
                    'label': 'NFO naming',
                    'default': '<filename>.<ext>-orig',
                },
                {
                    'name': 'trailer_name',
                    'label': 'Trailer naming',
                    'default': '<filename>-trailer.<ext>',
                },
            ],
        },
    ],
}]
