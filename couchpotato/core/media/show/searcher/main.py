import pprint
import re
from couchpotato import get_session, Env
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import getTitle, tryInt, possibleTitles
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media, Library
from caper import Caper

log = CPLog(__name__)


class ShowSearcher(Plugin):

    in_progress = False

    # TODO come back to this later, think this could be handled better
    quality_map = {
        'webdl_1080p': {'resolution': ['1080p'], 'source': ['webdl']},
        'webdl_720p': {'resolution': ['720p'], 'source': ['webdl']},

        'hdtv_720p': {'resolution': ['720p'], 'source': ['hdtv']},
        'hdtv_sd': {'resolution': ['480p', None], 'source': ['hdtv']},
    }

    def __init__(self):
        super(ShowSearcher, self).__init__()

        addEvent('show.searcher.single', self.single)
        addEvent('searcher.correct_release', self.correctRelease)
        addEvent('searcher.get_search_title', self.getSearchTitle)

        self.caper = Caper()

    def _lookupMedia(self, media):
        db = get_session()

        media_library = db.query(Library).filter_by(id = media['library_id']).first()

        show = None
        season = None
        episode = None

        if media['type'] == 'episode':
            show = media_library.parent.parent
            season = media_library.parent
            episode = media_library

        if media['type'] == 'season':
            show = media_library.parent
            season = media_library

        if media['type'] == 'show':
            show = media_library

        return show, season, episode

    def single(self, media, search_protocols = None):
        pprint.pprint(media)

        if media['type'] == 'show':
            # TODO handle show searches (scan all seasons)
            return

        # Find out search type
        try:
            if not search_protocols:
                search_protocols = fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return

        done_status = fireEvent('status.get', 'done', single = True)

        if not media['profile'] or media['status_id'] == done_status.get('id'):
            log.debug('Episode doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        pre_releases = fireEvent('quality.pre_releases', single = True)
        available_status, ignored_status, failed_status = fireEvent('status.get', ['available', 'ignored', 'failed'], single = True)

        found_releases = []
        too_early_to_search = []

        default_title = self.getSearchTitle(media['library'])
        if not default_title:
            log.error('No proper info found for episode, removing it from library to cause it from having more issues.')
            #fireEvent('episode.delete', episode['id'], single = True)
            return

        show, season, episode = self._lookupMedia(media)
        if show is None or season is None:
            log.error('Unable to find show or season library in database, missing required data for searching')
            return

        fireEvent('notify.frontend', type = 'show.searcher.started.%s' % media['id'], data = True, message = 'Searching for "%s"' % default_title)

        ret = False
        for quality_type in media['profile']['types']:
            # TODO check air date?
            #if not self.conf('always_search') and not self.couldBeReleased(quality_type['quality']['identifier'] in pre_releases, release_dates, movie['library']['year']):
            #    too_early_to_search.append(quality_type['quality']['identifier'])
            #    continue

            has_better_quality = 0

            # See if better quality is available
            for release in media['releases']:
                if release['quality']['order'] <= quality_type['quality']['order'] and release['status_id'] not in [available_status.get('id'), ignored_status.get('id'), failed_status.get('id')]:
                    has_better_quality += 1

            # Don't search for quality lower then already available.
            if has_better_quality is 0:

                log.info('Search for %s S%02d%s in %s', (getTitle(show), season.season_number, "E%02d" % episode.episode_number if episode else "", quality_type['quality']['label']))
                quality = fireEvent('quality.single', identifier = quality_type['quality']['identifier'], single = True)

                results = []
                for search_protocol in search_protocols:
                    protocol_results = fireEvent('provider.search.%s.show' % search_protocol, media, quality, merge = True)
                    if protocol_results:
                        results += protocol_results

                log.info('%d results found' % len(results))

    def correctRelease(self, release = None, media = None, quality = None, **kwargs):

        if media.get('type') not in ['season', 'episode']: return

        imdb_results = kwargs.get('imdb_results', False)
        retention = Env.setting('retention', section = 'nzb')

        if release.get('seeders') is None and 0 < retention < release.get('age', 0):
            log.info2('Wrong: Outside retention, age is %s, needs %s or lower: %s', (release['age'], retention, release['name']))
            return False

        # Check for required and ignored words
        if not fireEvent('searcher.correct_words', release['name'], media, single = True):
            return False

        #pprint.pprint(release)

        show, season, episode = self._lookupMedia(media)
        if show is None or season is None:
            log.error('Unable to find show or season library in database, missing required data for searching')
            return

        release_info = self.caper.parse(release['name'])
        if len(release_info.chains) < 1:
            log.info2('Wrong: %s, unable to parse release name (no chains)', release['name'])
            return False

        # TODO look at all chains
        chain = release_info.chains[0]

        if not self.correctQuality(chain, quality['identifier']):
            log.info('Wrong: %s, quality does not match', release['name'])
            return False

        if not self.correctIdentifier(chain, media):
            log.info('Wrong: %s, identifier does not match', release['name'])
            return False

        #print chain.weight
        #pprint.pprint(chain.info)

        if 'show_name' not in chain.info or not len(chain.info['show_name']):
            log.info('Wrong: %s, missing show name in parsed result', release['name'])
            return False

        chain_words = [x.lower() for x in chain.info['show_name']]
        chain_title = ' '.join(chain_words)

        library_title = None

        # Check show titles match
        for raw_title in show.titles:
            for valid_words in [x.split(' ') for x in possibleTitles(raw_title.title)]:
                if not library_title:
                    library_title = ' '.join(valid_words)

                if valid_words == chain_words:
                    return True

        log.info("Wrong: title '%s', undetermined show naming. Looking for '%s (%s)'", (chain_title, library_title, media['library']['year']))
        return False

    def correctQuality(self, chain, quality_identifier):
        if quality_identifier not in self.quality_map:
            log.info2('Wrong: unknown preferred quality %s for TV searching', quality_identifier)
            return False

        if 'video' not in chain.info:
            log.info2('Wrong: no video tags found')
            return False

        video_tags = self.quality_map[quality_identifier]

        if not self.chainMatches(chain, 'video', video_tags):
            log.info2('Wrong: %s tags not in chain', video_tags)
            return False

        return True

    def correctIdentifier(self, chain, media):
        required_id = self.getIdentifier(media['library'], 'season_number', 'episode_number')

        if 'identifier' not in chain.info:
            return False

        # TODO could be handled better?
        if len(chain.info['identifier']) != 1:
            return False
        identifier = chain.info['identifier'][0]

        # TODO air by date episodes
        release_id = self.getIdentifier(identifier, 'season', 'episode')

        if required_id != release_id:
            log.info2('Wrong: required identifier %s does not match release identifier %s', (str(required_id), str(release_id)))
            return False

        return True

    def getIdentifier(self, d, episode_key, season_key):
        return (
            tryInt(d.get(season_key), None) if season_key in d else None,
            tryInt(d.get(episode_key), None) if episode_key in d else None
        )

    def chainMatches(self, chain, group, tags):
        found_tags = []

        for match in chain.info[group]:
            for ck, cv in match.items():
                if ck in tags and self.cleanMatchValue(cv) in tags[ck]:
                    found_tags.append(ck)


        if set(tags.keys()) == set(found_tags):
            return True

        return set([key for key, value in tags.items() if value]) == set(found_tags)

    def cleanMatchValue(self, value):
        value = value.lower()
        value = value.strip()

        for ch in [' ', '-', '.']:
            value = value.replace(ch, '')

        return value

    def getSearchTitle(self, media):
        show, season, episode = self._lookupMedia(media)
        if show is None:
            return None

        name = ''
        if season is not None:
            name = ' S%02d' % season.season_number

            if episode is not None:
                name += 'E%02d' % episode.episode_number

        show_title = getTitle(show)
        if not show_title:
            return None

        return show_title + name
