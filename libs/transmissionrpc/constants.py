# -*- coding: utf-8 -*-
# Copyright (c) 2008-2011 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import logging

LOGGER = logging.getLogger('transmissionrpc')
LOGGER.setLevel(logging.ERROR)

def mirror_dict(source):
    """
    Creates a dictionary with all values as keys and all keys as values.
    """
    source.update(dict((value, key) for key, value in source.iteritems()))
    return source

DEFAULT_PORT = 9091

DEFAULT_TIMEOUT = 30.0

TR_PRI_LOW    = -1
TR_PRI_NORMAL =  0
TR_PRI_HIGH   =  1

PRIORITY = mirror_dict({
    'low'    : TR_PRI_LOW,
    'normal' : TR_PRI_NORMAL,
    'high'   : TR_PRI_HIGH
})

TR_RATIOLIMIT_GLOBAL    = 0 # follow the global settings
TR_RATIOLIMIT_SINGLE    = 1 # override the global settings, seeding until a certain ratio
TR_RATIOLIMIT_UNLIMITED = 2 # override the global settings, seeding regardless of ratio

RATIO_LIMIT = mirror_dict({
    'global'    : TR_RATIOLIMIT_GLOBAL,
    'single'    : TR_RATIOLIMIT_SINGLE,
    'unlimited' : TR_RATIOLIMIT_UNLIMITED
})

TR_IDLELIMIT_GLOBAL     = 0 # follow the global settings
TR_IDLELIMIT_SINGLE     = 1 # override the global settings, seeding until a certain idle time
TR_IDLELIMIT_UNLIMITED  = 2 # override the global settings, seeding regardless of activity

IDLE_LIMIT = mirror_dict({
    'global'    : TR_RATIOLIMIT_GLOBAL,
    'single'    : TR_RATIOLIMIT_SINGLE,
    'unlimited' : TR_RATIOLIMIT_UNLIMITED
})

# A note on argument maps
# These maps are used to verify *-set methods. The information is structured in
# a tree.
# set +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#  |  +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#  |
# get +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#     +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]

# Arguments for torrent methods
TORRENT_ARGS = {
    'get' : {
        'activityDate':                 ('number', 1, None, None, None, ''),
        'addedDate':                    ('number', 1, None, None, None, ''),
        'announceResponse':             ('string', 1, 7, None, None, ''),
        'announceURL':                  ('string', 1, 7, None, None, ''),
        'bandwidthPriority':            ('number', 5, None, None, None, ''),
        'comment':                      ('string', 1, None, None, None, ''),
        'corruptEver':                  ('number', 1, None, None, None, ''),
        'creator':                      ('string', 1, None, None, None, ''),
        'dateCreated':                  ('number', 1, None, None, None, ''),
        'desiredAvailable':             ('number', 1, None, None, None, ''),
        'doneDate':                     ('number', 1, None, None, None, ''),
        'downloadDir':                  ('string', 4, None, None, None, ''),
        'downloadedEver':               ('number', 1, None, None, None, ''),
        'downloaders':                  ('number', 4, 7, None, None, ''),
        'downloadLimit':                ('number', 1, None, None, None, ''),
        'downloadLimited':              ('boolean', 5, None, None, None, ''),
        'downloadLimitMode':            ('number', 1, 5, None, None, ''),
        'error':                        ('number', 1, None, None, None, ''),
        'errorString':                  ('number', 1, None, None, None, ''),
        'eta':                          ('number', 1, None, None, None, ''),
        'files':                        ('array', 1, None, None, None, ''),
        'fileStats':                    ('array', 5, None, None, None, ''),
        'hashString':                   ('string', 1, None, None, None, ''),
        'haveUnchecked':                ('number', 1, None, None, None, ''),
        'haveValid':                    ('number', 1, None, None, None, ''),
        'honorsSessionLimits':          ('boolean', 5, None, None, None, ''),
        'id':                           ('number', 1, None, None, None, ''),
        'isFinished':                   ('boolean', 9, None, None, None, ''),
        'isPrivate':                    ('boolean', 1, None, None, None, ''),
        'isStalled':                    ('boolean', 14, None, None, None, ''),
        'lastAnnounceTime':             ('number', 1, 7, None, None, ''),
        'lastScrapeTime':               ('number', 1, 7, None, None, ''),
        'leechers':                     ('number', 1, 7, None, None, ''),
        'leftUntilDone':                ('number', 1, None, None, None, ''),
        'magnetLink':                   ('string', 7, None, None, None, ''),
        'manualAnnounceTime':           ('number', 1, None, None, None, ''),
        'maxConnectedPeers':            ('number', 1, None, None, None, ''),
        'metadataPercentComplete':      ('number', 7, None, None, None, ''),
        'name':                         ('string', 1, None, None, None, ''),
        'nextAnnounceTime':             ('number', 1, 7, None, None, ''),
        'nextScrapeTime':               ('number', 1, 7, None, None, ''),
        'peer-limit':                   ('number', 5, None, None, None, ''),
        'peers':                        ('array', 2, None, None, None, ''),
        'peersConnected':               ('number', 1, None, None, None, ''),
        'peersFrom':                    ('object', 1, None, None, None, ''),
        'peersGettingFromUs':           ('number', 1, None, None, None, ''),
        'peersKnown':                   ('number', 1, 13, None, None, ''),
        'peersSendingToUs':             ('number', 1, None, None, None, ''),
        'percentDone':                  ('double', 5, None, None, None, ''),
        'pieces':                       ('string', 5, None, None, None, ''),
        'pieceCount':                   ('number', 1, None, None, None, ''),
        'pieceSize':                    ('number', 1, None, None, None, ''),
        'priorities':                   ('array', 1, None, None, None, ''),
        'queuePosition':                ('number', 14, None, None, None, ''),
        'rateDownload':                 ('number', 1, None, None, None, ''),
        'rateUpload':                   ('number', 1, None, None, None, ''),
        'recheckProgress':              ('double', 1, None, None, None, ''),
        'scrapeResponse':               ('string', 1, 7, None, None, ''),
        'scrapeURL':                    ('string', 1, 7, None, None, ''),
        'seeders':                      ('number', 1, 7, None, None, ''),
        'seedIdleLimit':                ('number', 10, None, None, None, ''),
        'seedIdleMode':                 ('number', 10, None, None, None, ''),
        'seedRatioLimit':               ('double', 5, None, None, None, ''),
        'seedRatioMode':                ('number', 5, None, None, None, ''),
        'sizeWhenDone':                 ('number', 1, None, None, None, ''),
        'startDate':                    ('number', 1, None, None, None, ''),
        'status':                       ('number', 1, None, None, None, ''),
        'swarmSpeed':                   ('number', 1, 7, None, None, ''),
        'timesCompleted':               ('number', 1, 7, None, None, ''),
        'trackers':                     ('array', 1, None, None, None, ''),
        'trackerStats':                 ('object', 7, None, None, None, ''),
        'totalSize':                    ('number', 1, None, None, None, ''),
        'torrentFile':                  ('string', 5, None, None, None, ''),
        'uploadedEver':                 ('number', 1, None, None, None, ''),
        'uploadLimit':                  ('number', 1, None, None, None, ''),
        'uploadLimitMode':              ('number', 1, 5, None, None, ''),
        'uploadLimited':                ('boolean', 5, None, None, None, ''),
        'uploadRatio':                  ('double', 1, None, None, None, ''),
        'wanted':                       ('array', 1, None, None, None, ''),
        'webseeds':                     ('array', 1, None, None, None, ''),
        'webseedsSendingToUs':          ('number', 1, None, None, None, ''),
    },
    'set': {
        'bandwidthPriority':            ('number', 5, None, None, None, 'Priority for this transfer.'),
        'downloadLimit':                ('number', 5, None, 'speed-limit-down', None, 'Set the speed limit for download in Kib/s.'),
        'downloadLimited':              ('boolean', 5, None, 'speed-limit-down-enabled', None, 'Enable download speed limiter.'),
        'files-wanted':                 ('array', 1, None, None, None, "A list of file id's that should be downloaded."),
        'files-unwanted':               ('array', 1, None, None, None, "A list of file id's that shouldn't be downloaded."),
        'honorsSessionLimits':          ('boolean', 5, None, None, None, "Enables or disables the transfer to honour the upload limit set in the session."),
        'location':                     ('array', 1, None, None, None, 'Local download location.'),
        'peer-limit':                   ('number', 1, None, None, None, 'The peer limit for the torrents.'),
        'priority-high':                ('array', 1, None, None, None, "A list of file id's that should have high priority."),
        'priority-low':                 ('array', 1, None, None, None, "A list of file id's that should have normal priority."),
        'priority-normal':              ('array', 1, None, None, None, "A list of file id's that should have low priority."),
        'queuePosition':                ('number', 14, None, None, None, 'Position of this transfer in its queue.'),
        'seedIdleLimit':                ('number', 10, None, None, None, 'Seed inactivity limit in minutes.'),
        'seedIdleMode':                 ('number', 10, None, None, None, 'Seed inactivity mode. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.'),
        'seedRatioLimit':               ('double', 5, None, None, None, 'Seeding ratio.'),
        'seedRatioMode':                ('number', 5, None, None, None, 'Which ratio to use. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.'),
        'speed-limit-down':             ('number', 1, 5, None, 'downloadLimit', 'Set the speed limit for download in Kib/s.'),
        'speed-limit-down-enabled':     ('boolean', 1, 5, None, 'downloadLimited', 'Enable download speed limiter.'),
        'speed-limit-up':               ('number', 1, 5, None, 'uploadLimit', 'Set the speed limit for upload in Kib/s.'),
        'speed-limit-up-enabled':       ('boolean', 1, 5, None, 'uploadLimited', 'Enable upload speed limiter.'),
        'trackerAdd':                   ('array', 10, None, None, None, 'Array of string with announce URLs to add.'),
        'trackerRemove':                ('array', 10, None, None, None, 'Array of ids of trackers to remove.'),
        'trackerReplace':               ('array', 10, None, None, None, 'Array of (id, url) tuples where the announce URL should be replaced.'),
        'uploadLimit':                  ('number', 5, None, 'speed-limit-up', None, 'Set the speed limit for upload in Kib/s.'),
        'uploadLimited':                ('boolean', 5, None, 'speed-limit-up-enabled', None, 'Enable upload speed limiter.'),
    },
    'add': {
        'bandwidthPriority':            ('number', 8, None, None, None, 'Priority for this transfer.'),
        'download-dir':                 ('string', 1, None, None, None, 'The directory where the downloaded contents will be saved in.'),
        'cookies':                      ('string', 13, None, None, None, 'One or more HTTP cookie(s).'),
        'filename':                     ('string', 1, None, None, None, "A file path or URL to a torrent file or a magnet link."),
        'files-wanted':                 ('array', 1, None, None, None, "A list of file id's that should be downloaded."),
        'files-unwanted':               ('array', 1, None, None, None, "A list of file id's that shouldn't be downloaded."),
        'metainfo':                     ('string', 1, None, None, None, 'The content of a torrent file, base64 encoded.'),
        'paused':                       ('boolean', 1, None, None, None, 'If True, does not start the transfer when added.'),
        'peer-limit':                   ('number', 1, None, None, None, 'Maximum number of peers allowed.'),
        'priority-high':                ('array', 1, None, None, None, "A list of file id's that should have high priority."),
        'priority-low':                 ('array', 1, None, None, None, "A list of file id's that should have low priority."),
        'priority-normal':              ('array', 1, None, None, None, "A list of file id's that should have normal priority."),
    }
}

# Arguments for session methods
SESSION_ARGS = {
    'get': {
        "alt-speed-down":               ('number', 5, None, None, None, ''),
        "alt-speed-enabled":            ('boolean', 5, None, None, None, ''),
        "alt-speed-time-begin":         ('number', 5, None, None, None, ''),
        "alt-speed-time-enabled":       ('boolean', 5, None, None, None, ''),
        "alt-speed-time-end":           ('number', 5, None, None, None, ''),
        "alt-speed-time-day":           ('number', 5, None, None, None, ''),
        "alt-speed-up":                 ('number', 5, None, None, None, ''),
        "blocklist-enabled":            ('boolean', 5, None, None, None, ''),
        "blocklist-size":               ('number', 5, None, None, None, ''),
        "blocklist-url":                ('string', 11, None, None, None, ''),
        "cache-size-mb":                ('number', 10, None, None, None, ''),
        "config-dir":                   ('string', 8, None, None, None, ''),
        "dht-enabled":                  ('boolean', 6, None, None, None, ''),
        "download-dir":                 ('string', 1, None, None, None, ''),
        "download-dir-free-space":      ('number', 12, None, None, None, ''),
        "download-queue-size":          ('number', 14, None, None, None, ''),
        "download-queue-enabled":       ('boolean', 14, None, None, None, ''),
        "encryption":                   ('string', 1, None, None, None, ''),
        "idle-seeding-limit":           ('number', 10, None, None, None, ''),
        "idle-seeding-limit-enabled":   ('boolean', 10, None, None, None, ''),
        "incomplete-dir":               ('string', 7, None, None, None, ''),
        "incomplete-dir-enabled":       ('boolean', 7, None, None, None, ''),
        "lpd-enabled":                  ('boolean', 9, None, None, None, ''),
        "peer-limit":                   ('number', 1, 5, None, None, ''),
        "peer-limit-global":            ('number', 5, None, None, None, ''),
        "peer-limit-per-torrent":       ('number', 5, None, None, None, ''),
        "pex-allowed":                  ('boolean', 1, 5, None, None, ''),
        "pex-enabled":                  ('boolean', 5, None, None, None, ''),
        "port":                         ('number', 1, 5, None, None, ''),
        "peer-port":                    ('number', 5, None, None, None, ''),
        "peer-port-random-on-start":    ('boolean', 5, None, None, None, ''),
        "port-forwarding-enabled":      ('boolean', 1, None, None, None, ''),
        "queue-stalled-minutes":        ('number', 14, None, None, None, ''),
        "queue-stalled-enabled":        ('boolean', 14, None, None, None, ''),
        "rename-partial-files":         ('boolean', 8, None, None, None, ''),
        "rpc-version":                  ('number', 4, None, None, None, ''),
        "rpc-version-minimum":          ('number', 4, None, None, None, ''),
        "script-torrent-done-enabled":  ('boolean', 9, None, None, None, ''),
        "script-torrent-done-filename": ('string', 9, None, None, None, ''),
        "seedRatioLimit":               ('double', 5, None, None, None, ''),
        "seedRatioLimited":             ('boolean', 5, None, None, None, ''),
        "seed-queue-size":              ('number', 14, None, None, None, ''),
        "seed-queue-enabled":           ('boolean', 14, None, None, None, ''),
        "speed-limit-down":             ('number', 1, None, None, None, ''),
        "speed-limit-down-enabled":     ('boolean', 1, None, None, None, ''),
        "speed-limit-up":               ('number', 1, None, None, None, ''),
        "speed-limit-up-enabled":       ('boolean', 1, None, None, None, ''),
        "start-added-torrents":         ('boolean', 9, None, None, None, ''),
        "trash-original-torrent-files": ('boolean', 9, None, None, None, ''),
        'units':                        ('object', 10, None, None, None, ''),
        'utp-enabled':                  ('boolean', 13, None, None, None, ''),
        "version":                      ('string', 3, None, None, None, ''),
    },
    'set': {
        "alt-speed-down":               ('number', 5, None, None, None, 'Alternate session download speed limit (in Kib/s).'),
        "alt-speed-enabled":            ('boolean', 5, None, None, None, 'Enables alternate global download speed limiter.'),
        "alt-speed-time-begin":         ('number', 5, None, None, None, 'Time when alternate speeds should be enabled. Minutes after midnight.'),
        "alt-speed-time-enabled":       ('boolean', 5, None, None, None, 'Enables alternate speeds scheduling.'),
        "alt-speed-time-end":           ('number', 5, None, None, None, 'Time when alternate speeds should be disabled. Minutes after midnight.'),
        "alt-speed-time-day":           ('number', 5, None, None, None, 'Enables alternate speeds scheduling these days.'),
        "alt-speed-up":                 ('number', 5, None, None, None, 'Alternate session upload speed limit (in Kib/s).'),
        "blocklist-enabled":            ('boolean', 5, None, None, None, 'Enables the block list'),
        "blocklist-url":                ('string', 11, None, None, None, 'Location of the block list. Updated with blocklist-update.'),
        "cache-size-mb":                ('number', 10, None, None, None, 'The maximum size of the disk cache in MB'),
        "dht-enabled":                  ('boolean', 6, None, None, None, 'Enables DHT.'),
        "download-dir":                 ('string', 1, None, None, None, 'Set the session download directory.'),
        "download-queue-size":          ('number', 14, None, None, None, 'Number of parallel downloads.'),
        "download-queue-enabled":       ('boolean', 14, None, None, None, 'Enable parallel download restriction.'),
        "encryption":                   ('string', 1, None, None, None, 'Set the session encryption mode, one of ``required``, ``preferred`` or ``tolerated``.'),
        "idle-seeding-limit":           ('number', 10, None, None, None, 'The default seed inactivity limit in minutes.'),
        "idle-seeding-limit-enabled":   ('boolean', 10, None, None, None, 'Enables the default seed inactivity limit'),
        "incomplete-dir":               ('string', 7, None, None, None, 'The path to the directory of incomplete transfer data.'),
        "incomplete-dir-enabled":       ('boolean', 7, None, None, None, 'Enables the incomplete transfer data directory. Otherwise data for incomplete transfers are stored in the download target.'),
        "lpd-enabled":                  ('boolean', 9, None, None, None, 'Enables local peer discovery for public torrents.'),
        "peer-limit":                   ('number', 1, 5, None, 'peer-limit-global', 'Maximum number of peers'),
        "peer-limit-global":            ('number', 5, None, 'peer-limit', None, 'Maximum number of peers'),
        "peer-limit-per-torrent":       ('number', 5, None, None, None, 'Maximum number of peers per transfer'),
        "pex-allowed":                  ('boolean', 1, 5, None, 'pex-enabled', 'Allowing PEX in public torrents.'),
        "pex-enabled":                  ('boolean', 5, None, 'pex-allowed', None, 'Allowing PEX in public torrents.'),
        "port":                         ('number', 1, 5, None, 'peer-port', 'Peer port.'),
        "peer-port":                    ('number', 5, None, 'port', None, 'Peer port.'),
        "peer-port-random-on-start":    ('boolean', 5, None, None, None, 'Enables randomized peer port on start of Transmission.'),
        "port-forwarding-enabled":      ('boolean', 1, None, None, None, 'Enables port forwarding.'),
        "rename-partial-files":         ('boolean', 8, None, None, None, 'Appends ".part" to incomplete files'),
        "queue-stalled-minutes":        ('number', 14, None, None, None, 'Number of minutes of idle that marks a transfer as stalled.'),
        "queue-stalled-enabled":        ('boolean', 14, None, None, None, 'Enable tracking of stalled transfers.'),
        "script-torrent-done-enabled":  ('boolean', 9, None, None, None, 'Whether or not to call the "done" script.'),
        "script-torrent-done-filename": ('string', 9, None, None, None, 'Filename of the script to run when the transfer is done.'),
        "seed-queue-size":              ('number', 14, None, None, None, 'Number of parallel uploads.'),
        "seed-queue-enabled":           ('boolean', 14, None, None, None, 'Enable parallel upload restriction.'),
        "seedRatioLimit":               ('double', 5, None, None, None, 'Seed ratio limit. 1.0 means 1:1 download and upload ratio.'),
        "seedRatioLimited":             ('boolean', 5, None, None, None, 'Enables seed ration limit.'),
        "speed-limit-down":             ('number', 1, None, None, None, 'Download speed limit (in Kib/s).'),
        "speed-limit-down-enabled":     ('boolean', 1, None, None, None, 'Enables download speed limiting.'),
        "speed-limit-up":               ('number', 1, None, None, None, 'Upload speed limit (in Kib/s).'),
        "speed-limit-up-enabled":       ('boolean', 1, None, None, None, 'Enables upload speed limiting.'),
        "start-added-torrents":         ('boolean', 9, None, None, None, 'Added torrents will be started right away.'),
        "trash-original-torrent-files": ('boolean', 9, None, None, None, 'The .torrent file of added torrents will be deleted.'),
        'utp-enabled':                  ('boolean', 13, None, None, None, 'Enables Micro Transport Protocol (UTP).'),
    },
}
