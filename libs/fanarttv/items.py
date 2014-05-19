import json
import os
import libs.requests as requests
from libs.fanarttv.core import Request
from libs.fanarttv.immutable import Immutable


class LeafItem(Immutable):
    KEY = NotImplemented

    @Immutable.mutablemethod
    def __init__(self, id, url, likes):
        self.id = int(id)
        self.url = url
        self.likes = int(likes)
        self._content = None

    @classmethod
    def from_dict(cls, resource):
        return cls(**dict([(str(k), v) for k, v in resource.iteritems()]))

    @classmethod
    def extract(cls, resource):
        return [cls.from_dict(i) for i in resource.get(cls.KEY, {})]

    @Immutable.mutablemethod
    def content(self):
        if not self._content:
            self._content = requests.get(self.url).content
        return self._content

    def __str__(self):
        return self.url


class ResourceItem(Immutable):
    WS = NotImplemented
    request_cls = Request

    @classmethod
    def from_dict(cls, map):
        raise NotImplementedError

    @classmethod
    def get(cls, id):
        map = cls.request_cls(
            apikey=os.environ.get('FANART_APIKEY'),
            id=id,
            ws=cls.WS
        ).response()
        return cls.from_dict(map)

    def json(self, **kw):
        return json.dumps(
            self,
            default=lambda o: dict([(k, v) for k, v in o.__dict__.items() if not k.startswith('_')]),
            **kw
        )


class CollectableItem(Immutable):
    @classmethod
    def from_dict(cls, key, map):
        raise NotImplementedError

    @classmethod
    def collection_from_dict(cls, map):
        return [cls.from_dict(k, v) for k, v in map.iteritems()]
