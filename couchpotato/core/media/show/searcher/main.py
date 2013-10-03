from couchpotato import get_session, Env
from couchpotato.core.event import addEvent, fireEvent
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
        addEvent('searcher.get_media_searcher_id', self.getMediaSearcherId)

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

    def single(self, media, search_protocols = None, manual = False):
        if media['type'] == 'show':
            # TODO handle show searches (scan all seasons)
            return

        # Find out search type
        try:
            if not search_protocols:
                search_protocols = fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return

        done_status, available_status, ignored_status, failed_status = fireEvent('status.get', ['done', 'available', 'ignored', 'failed'], single = True)

        if not media['profile'] or media['status_id'] == done_status.get('id'):
            log.debug('Episode doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        #pre_releases = fireEvent('quality.pre_releases', single = True)

        found_releases = []
        too_early_to_search = []

        default_title = self.getSearchTitle(media)
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

                results = fireEvent('searcher.search', search_protocols, media, quality, single = True)
                if len(results) == 0:
                    log.debug('Nothing found for %s in %s', (default_title, quality_type['quality']['label']))

                # Check if movie isn't deleted while searching
                if not db.query(Media).filter_by(id = media.get('id')).first():
                    break

                # Add them to this movie releases list
                found_releases += fireEvent('searcher.create_releases', results, media, quality_type, single = True)

                # Try find a valid result and download it
                if fireEvent('searcher.try_download_result', results, media, quality_type, manual, single = True):
                    ret = True

                # Remove releases that aren't found anymore
                for release in media.get('releases', []):
                    if release.get('status_id') == available_status.get('id') and release.get('identifier') not in found_releases:
                        fireEvent('release.delete', release.get('id'), single = True)
            else:
                log.info('Better quality (%s) already available or snatched for %s', (quality_type['quality']['label'], default_title))
                fireEvent('movie.restatus', media['id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, default_title))

        fireEvent('notify.frontend', type = 'show.searcher.ended.%s' % media['id'], data = True)

        return ret

    def correctRelease(self, release = None, media = None, quality = None, **kwargs):

        if media.get('type') not in ['season', 'episode']: return

        retention = Env.setting('retention', section = 'nzb')

        if release.get('seeders') is None and 0 < retention < release.get('age', 0):
            log.info2('Wrong: Outside retention, age is %s, needs %s or lower: %s', (release['age'], retention, release['name']))
            return False

        # Check for required and ignored words
        if not fireEvent('searcher.correct_words', release['name'], media, single = True):
            return False

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
                    return chain.weight

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
        required_id = self.getMediaIdentifier(media['library'])

        if 'identifier' not in chain.info:
            return False

        # TODO could be handled better?
        if len(chain.info['identifier']) != 1:
            return False
        identifier = chain.info['identifier'][0]

        # TODO air by date episodes
        release_id = self.toNumericIdentifier(identifier.get('season'), identifier.get('episode'))

        if required_id != release_id:
            log.info2('Wrong: required identifier %s does not match release identifier %s', (str(required_id), str(release_id)))
            return False

        return True

    def getMediaIdentifier(self, media_library):
        identifier = None, None

        if media_library['type'] == 'episode':
            map_episode = media_library['info'].get('map_episode')

            if map_episode and 'scene' in map_episode:
                identifier = (
                    map_episode['scene'].get('season'),
                    map_episode['scene'].get('episode')
                )
            else:
                # TODO xem mapping?
                identifier = (
                    media_library.get('season_number'),
                    media_library.get('episode_number')
                )

        if media_library['type'] == 'season':
            identifier = media_library.get('season_number'), None

        return self.toNumericIdentifier(*identifier)

    def toNumericIdentifier(self, season, episode):
        return tryInt(season, None), tryInt(episode, None)

    def chainMatches(self, chain, group, tags):
        found_tags = []

        for match in chain.info[group]:
            for ck, cv in match.items():
                if ck in tags and self.cleanMatchValue(cv) in tags[ck]:
                    found_tags.append(ck)


        if set(tags.keys()) == set(found_tags):
            return True

        return set([key for key, value in tags.items() if None not in value]) == set(found_tags)

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

        # TODO this misses alternative titles from the database
        show_title = getTitle(show)
        if not show_title:
            return None

        season_num, episode_num = self.getMediaIdentifier(media['library'])

        name = show_title

        if season_num:
            name += ' S%02d' % season_num

            if episode_num:
                name += 'E%02d' % episode_num

        return name

    def getMediaSearcherId(self, media_type):
        if media_type in ['show', 'season', 'episode']:
            return 'show'
