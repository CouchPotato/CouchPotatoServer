import os
import traceback

from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.base import MovieProvider
from couchpotato.core.plugins.quality import QualityPlugin
import libs.fanarttv.errors as fanarttv_errors
from libs.fanarttv.movie import Movie


log = CPLog(__name__)

autoload = 'FanartTV'


class FanartTV(MovieProvider):

    MAX_EXTRAFANART = 20

    def __init__(self):
        addEvent('movie.extra_art', self.getArt, priority=2)

        # Configure fanarttv API settings
        os.environ.setdefault('FANART_APIKEY', self.conf('api_key'))

    def getArt(self, identifier):
        # FIXME: I believe I should be registering a cache here... I need to look into that.
        log.debug("Getting Extra Artwork from Fanart.tv...")
        if not identifier:
            return {}

        images = {}

        try:
            try:
                exists = True
                movie = Movie.get(id = identifier)
            except (fanarttv_errors.FanartError, IOError):
                exists = False

            if exists:
                images = self._parseMovie(movie, True)

        except:
            log.error('Failed getting extra art for %s: %s',
                      (identifier, traceback.format_exc()))
            return {}

        return images

    def _parseMovie(self, movie, is_hd):
        images = {
            'landscape': [],
            'logo': [],
            'disc_art': [],
            'clear_art': [],
            'banner': [],
            'extra_fanart': [],
        }

        images['landscape'] = self._getMultImages(movie.thumbs, 1)
        images['banner'] = self._getMultImages(movie.banners, 1)
        images['disc_art'] = self._getMultImages(self._trimDiscs(movie.discs, is_hd), 1)

        images['clear_art'] = self._getMultImages(movie.hdarts, 1)
        if len(images['clear_art']) is 0:
            images['clear_art'] = self._getMultImages(movie.arts, 1)

        images['logo'] = self._getMultImages(movie.hdlogos, 1)
        if len(images['logo']) is 0:
            images['logo'] = self._getMultImages(movie.logos, 1)

        fanarts = self._getMultImages(movie.backgrounds, self.MAX_EXTRAFANART + 1)

        if fanarts:
            images['backdrop_original'] = fanarts[0]
            images['extra_fanart'] = fanarts[1:]

        # TODO: Add support for extra backgrounds
        #extra_fanart = self._getMultImages(movie.backgrounds, -1)

        return images

    def _trimDiscs(self, disc_images, is_hd):
        """
        Return a subset of discImages based on isHD.  If isHD is true, only 
        bluray disc images will be returned.  If isHD is false, only dvd disc 
        images will be returned.  If the resulting list would be an empty list,
        then the original list is returned instead.
        """

        trimmed = []
        for disc in disc_images:
            if is_hd and disc.disc_type == u'bluray':
                trimmed.append(disc)
            elif not is_hd and disc.disc_type == u'dvd':
                trimmed.append(disc)

        if len(trimmed) is 0:
            return disc_images
        else:
            return trimmed

    def _getImage(self, images):
        image_url = None
        highscore = -1
        for image in images:
            if image.likes > highscore:
                highscore = image.likes
                image_url = image.url

        return image_url

    def _getMultImages(self, images, n):
        '''
        Chooses the best n images and returns them as a list.
        If n<0, all images will be returned.
        '''
        image_urls = []
        pool = []
        for image in images:
            if image.lang == u'en':
                pool.append(image)
        orig_pool_size = len(pool)

        while len(pool) > 0 and (n < 0 or orig_pool_size - len(pool) < n):
            best = None
            highscore = -1
            for image in pool:
                if image.likes > highscore:
                    highscore = image.likes
                    best = image
            image_urls.append(best.url)
            pool.remove(best)

        return image_urls

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('No API key provided.')
            return True
        return False

    def _determineHD(self, quality):
        for qualityDef in QualityPlugin.qualities:
            if quality == qualityDef.get('identifier'):
                return bool(qualityDef.get('hd'))
        return False


config = [{
    'name': 'fanarttv',
    'groups': [
        {
            'tab': 'providers',
            'name': 'fanarttv',
            'label': 'fanart.tv',
            'hidden': True,
            'description': 'Used for all calls to fanart.tv.',
            'options': [
                {
                    'name': 'api_key',
                    'default': 'd788b4822b9e1f44068026e05557e5d9',
                    'label': 'API Key',
                },
            ],
        },
    ],
}]
