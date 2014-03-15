from urlparse import urljoin
import logging

log = logging.getLogger(__name__)


class Base(object):
    properties = {}

    def __init__(self, url, session, client=None):
        self._client = client
        self._url = url
        self._session = session

    @staticmethod
    def _convert(response, response_type):
        if response_type == 'json':
            try:
                return response.json()
            except ValueError:
                pass

        return response

    def _get(self, path='', response_type='json', **kwargs):
        r = self._session.get(urljoin(self._url, path), **kwargs)
        return self._convert(r, response_type)

    def _post(self, path='', response_type='json', data=None, **kwargs):
        r = self._session.post(urljoin(self._url, path), data, **kwargs)
        return self._convert(r, response_type)

    def _fill(self, data):
        for key, value in data.items():
            if self.set_property(self, key, value):
                continue

            log.debug('%s is missing item with key "%s" and value %s', self.__class__, key, repr(value))

    @classmethod
    def parse(cls, client, data):
        obj = cls(client._url, client._session, client)
        obj._fill(data)

        return obj

    @classmethod
    def set_property(cls, obj, key, value):
        prop = cls.properties.get(key, {})

        if prop.get('key'):
            key = prop['key']

        if not hasattr(obj, key):
            return False


        if prop.get('parse'):
            value = prop['parse'](value)

        setattr(obj, key, value)
        return True
