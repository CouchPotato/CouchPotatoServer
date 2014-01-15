from couchpotato.core.plugins.renamer.main import Renamer
import os

def start():
    return Renamer()

rename_options = {
    'pre': '<',
    'post': '>',
    'choices': {
        'ext': 'Extention (mkv)',
        'namethe': 'Moviename, The',
        'thename': 'The Moviename',
        'year': 'Year (2011)',
        'first': 'First letter (M)',
        'quality': 'Quality (720p)',
        'quality_type': '(HD) or (SD)',
        'video': 'Video (x264)',
        'audio': 'Audio (DTS)',
        'group': 'Releasegroup name',
        'source': 'Source media (Bluray)',
        'resolution_width': 'resolution width (1280)',
        'resolution_height': 'resolution height (720)',
        'audio_channels': 'audio channels (7.1)',
        'original': 'Original filename',
        'original_folder': 'Original foldername',
        'imdb_id': 'IMDB id (tt0123456)',
        'cd': 'CD number (cd1)',
        'cd_nr': 'Just the cd nr. (1)',
        'mpaa': 'MPAA Rating',
        'category': 'Category label',
    },
}

config = [{
    'name': 'renamer',
    'order': 40,
    'description': 'Move and rename your downloaded movies to your movie directory.',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'renamer',
            'label': 'Rename downloaded movies',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'from',
                    'type': 'directory',
                    'description': 'Folder where CP searches for movies.',
                },
                {
                    'name': 'to',
                    'type': 'directory',
                    'description': 'Default folder where the movies are moved to.',
                },
                {
                    'name': 'folder_name',
                    'label': 'Folder naming',
                    'description': 'Name of the folder. Keep empty for no folder.',
                    'default': '<namethe> (<year>)',
                    'type': 'choice',
                    'options': rename_options
                },
                {
                    'name': 'file_name',
                    'label': 'File naming',
                    'description': 'Name of the file',
                    'default': '<thename><cd>.<ext>',
                    'type': 'choice',
                    'options': rename_options
                },
                {
                    'name': 'unrar',
                    'type': 'bool',
                    'description': 'Extract rar files if found.',
                    'default': False,
                },
                {
                    'name': 'cleanup',
                    'type': 'bool',
                    'description': 'Cleanup leftover files after successful rename.',
                    'default': False,
                },
                {
                    'advanced': True,
                    'name': 'run_every',
                    'label': 'Run every',
                    'default': 1,
                    'type': 'int',
                    'unit': 'min(s)',
                    'description': ('Detect movie status every X minutes.', 'Will start the renamer if movie is <strong>completed</strong> or handle <strong>failed</strong> download if these options are enabled'),
                },
                {
                    'advanced': True,
                    'name': 'force_every',
                    'label': 'Force every',
                    'default': 2,
                    'type': 'int',
                    'unit': 'hour(s)',
                    'description': 'Forces the renamer to scan every X hours',
                },
                {
                    'advanced': True,
                    'name': 'next_on_failed',
                    'default': True,
                    'type': 'bool',
                    'description': 'Try the next best release for a movie after a download failed.',
                },
                {
                    'name': 'move_leftover',
                    'type': 'bool',
                    'description': 'Move all leftover file after renaming, to the movie folder.',
                    'default': False,
                    'advanced': True,
                },
                {
                    'advanced': True,
                    'name': 'separator',
                    'label': 'File-Separator',
                    'description': ('Replace all the spaces with a character.', 'Example: ".", "-" (without quotes). Leave empty to use spaces.'),
                },
                {
                    'advanced': True,
                    'name': 'foldersep',
                    'label': 'Folder-Separator',
                    'description': ('Replace all the spaces with a character.', 'Example: ".", "-" (without quotes). Leave empty to use spaces.'),
                },
                {
                    'name': 'file_action',
                    'label': 'Torrent File Action',
                    'default': 'link',
                    'type': 'dropdown',
                    'values': [('Link', 'link'), ('Copy', 'copy'), ('Move', 'move')],
                    'description': ('<strong>Link</strong>, <strong>Copy</strong> or <strong>Move</strong> after download completed.', 'Link first tries <a href="http://en.wikipedia.org/wiki/Hard_link">hard link</a>, then <a href="http://en.wikipedia.org/wiki/Sym_link">sym link</a> and falls back to Copy. It is perfered to use link when downloading torrents as it will save you space, while still beeing able to seed.'),
                    'advanced': True,
                },
                {
                    'advanced': True,
                    'name': 'ntfs_permission',
                    'label': 'NTFS Permission',
                    'type': 'bool',
                    'hidden': os.name != 'nt',
                    'description': 'Set permission of moved files to that of destination folder (Windows NTFS only).',
                    'default': False,
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
                    'default': '<filename>.orig.<ext>',
                    'type': 'choice',
                    'options': rename_options
                },
            ],
        },
    ],
}]
