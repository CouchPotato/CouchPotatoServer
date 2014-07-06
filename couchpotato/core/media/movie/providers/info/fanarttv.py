import traceback

from couchpotato import tryInt
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.base import MovieProvider


log = CPLog(__name__)

autoload = 'FanartTV'


class FanartTV(MovieProvider):

    urls = {
        'api': 'http://api.fanart.tv/webservice/movie/b28b14e9be662e027cfbc7c3dd600405/%s/JSON/all/1/2'
    }

    MAX_EXTRAFANART = 20
    http_time_between_calls = 0

    def __init__(self):
        addEvent('movie.info', self.getArt, priority = 1)

    def getArt(self, identifier = None, **kwargs):

        log.debug("Getting Extra Artwork from Fanart.tv...")
        if not identifier:
            return {}

        images = {}

        try:
            url = self.urls['api'] % identifier
            fanart_data = self.getJsonData(url)

            if fanart_data:
                name, resource = fanart_data.items()[0]
                log.debug('Found images for %s', name)
                images = self._parseMovie(resource)

        except:
            log.error('Failed getting extra art for %s: %s',
                      (identifier, traceback.format_exc()))
            return {}

        return {
            'images': images
        }

    def _parseMovie(self, movie):
        images = {
            'landscape': self._getMultImages(movie.get('moviethumb', []), 1),
            'logo': [],
            'disc_art': self._getMultImages(self._trimDiscs(movie.get('moviedisc', [])), 1),
            'clear_art': self._getMultImages(movie.get('hdmovieart', []), 1),
            'banner': self._getMultImages(movie.get('moviebanner', []), 1),
            'extra_fanart': [],
        }

        if len(images['clear_art']) == 0:
            images['clear_art'] = self._getMultImages(movie.get('movieart', []), 1)

        images['logo'] = self._getMultImages(movie.get('hdmovielogo', []), 1)
        if len(images['logo']) == 0:
            images['logo'] = self._getMultImages(movie.get('movielogo', []), 1)

        fanarts = self._getMultImages(movie.get('moviebackground', []), self.MAX_EXTRAFANART + 1)

        if fanarts:
            images['backdrop_original'] = [fanarts[0]]
            images['extra_fanart'] = fanarts[1:]

        return images

    def _trimDiscs(self, disc_images):
        """
        Return a subset of discImages. Only bluray disc images will be returned.
        """

        trimmed = []
        for disc in disc_images:
            if disc.get('disc_type') == 'bluray':
                trimmed.append(disc)

        if len(trimmed) == 0:
            return disc_images

        return trimmed

    def _getImage(self, images):
        image_url = None
        highscore = -1
        for image in images:
            if tryInt(image.get('likes')) > highscore:
                highscore = tryInt(image.get('likes'))
                image_url = image.get('url')

        return image_url

    def _getMultImages(self, images, n):
        """
        Chooses the best n images and returns them as a list.
        If n<0, all images will be returned.
        """
        image_urls = []
        pool = []
        for image in images:
            if image.get('lang') == 'en':
                pool.append(image)
        orig_pool_size = len(pool)

        while len(pool) > 0 and (n < 0 or orig_pool_size - len(pool) < n):
            best = None
            highscore = -1
            for image in pool:
                if tryInt(image.get('likes')) > highscore:
                    highscore = tryInt(image.get('likes'))
                    best = image
            image_urls.append(best.get('url'))
            pool.remove(best)

        return image_urls

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('No API key provided.')
            return True
        return False
