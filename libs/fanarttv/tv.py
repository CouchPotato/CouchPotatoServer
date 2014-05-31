import libs.fanarttv as fanart
from libs.fanarttv.items import LeafItem, Immutable, ResourceItem
__all__ = (
    'CharacterItem',
    'ArtItem',
    'LogoItem',
    'BackgroundItem',
    'SeasonItem',
    'ThumbItem',
    'HdLogoItem',
    'HdArtItem',
    'PosterItem',
    'BannerItem',
    'TvShow',
)


class TvItem(LeafItem):
    @Immutable.mutablemethod
    def __init__(self, id, url, likes, lang):
        super(TvItem, self).__init__(id, url, likes)
        self.lang = lang


class SeasonedTvItem(TvItem):
    @Immutable.mutablemethod
    def __init__(self, id, url, likes, lang, season):
        super(SeasonedTvItem, self).__init__(id, url, likes, lang)
        self.season = 0 if season == 'all' else int(season or 0)


class CharacterItem(TvItem):
    KEY = fanart.TYPE.TV.CHARACTER


class ArtItem(TvItem):
    KEY = fanart.TYPE.TV.ART


class LogoItem(TvItem):
    KEY = fanart.TYPE.TV.LOGO


class BackgroundItem(SeasonedTvItem):
    KEY = fanart.TYPE.TV.BACKGROUND


class SeasonItem(SeasonedTvItem):
    KEY = fanart.TYPE.TV.SEASONTHUMB


class ThumbItem(TvItem):
    KEY = fanart.TYPE.TV.THUMB


class HdLogoItem(TvItem):
    KEY = fanart.TYPE.TV.HDLOGO


class HdArtItem(TvItem):
    KEY = fanart.TYPE.TV.HDART


class PosterItem(TvItem):
    KEY = fanart.TYPE.TV.POSTER


class BannerItem(TvItem):
    KEY = fanart.TYPE.TV.BANNER


class TvShow(ResourceItem):
    WS = fanart.WS.TV

    @Immutable.mutablemethod
    def __init__(self, name, tvdbid, backgrounds, characters, arts, logos, seasons, thumbs, hdlogos, hdarts, posters,
                 banners):
        self.name = name
        self.tvdbid = tvdbid
        self.backgrounds = backgrounds
        self.characters = characters
        self.arts = arts
        self.logos = logos
        self.seasons = seasons
        self.thumbs = thumbs
        self.hdlogos = hdlogos
        self.hdarts = hdarts
        self.posters = posters
        self.banners = banners

    @classmethod
    def from_dict(cls, resource):
        assert len(resource) == 1, 'Bad Format Map'
        name, resource = resource.items()[0]
        return cls(
            name=name,
            tvdbid=resource['thetvdb_id'],
            backgrounds=BackgroundItem.extract(resource),
            characters=CharacterItem.extract(resource),
            arts=ArtItem.extract(resource),
            logos=LogoItem.extract(resource),
            seasons=SeasonItem.extract(resource),
            thumbs=ThumbItem.extract(resource),
            hdlogos=HdLogoItem.extract(resource),
            hdarts=HdArtItem.extract(resource),
            posters=PosterItem.extract(resource),
            banners=BannerItem.extract(resource),
        )
