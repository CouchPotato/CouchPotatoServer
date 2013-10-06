#!/usr/bin/env python

import sys
import unittest

# Allow direct execution
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_dl.extractor import YoutubeIE, YoutubePlaylistIE, YoutubeChannelIE, JustinTVIE, gen_extractors
from helper import get_testcases

class TestAllURLsMatching(unittest.TestCase):
    def setUp(self):
        self.ies = gen_extractors()

    def matching_ies(self, url):
        return [ie.IE_NAME for ie in self.ies if ie.suitable(url) and ie.IE_NAME != 'generic']

    def assertMatch(self, url, ie_list):
        self.assertEqual(self.matching_ies(url), ie_list)

    def test_youtube_playlist_matching(self):
        assertPlaylist = lambda url: self.assertMatch(url, ['youtube:playlist'])
        assertPlaylist(u'ECUl4u3cNGP61MdtwGTqZA0MreSaDybji8')
        assertPlaylist(u'UUBABnxM4Ar9ten8Mdjj1j0Q') #585
        assertPlaylist(u'PL63F0C78739B09958')
        assertPlaylist(u'https://www.youtube.com/playlist?list=UUBABnxM4Ar9ten8Mdjj1j0Q')
        assertPlaylist(u'https://www.youtube.com/course?list=ECUl4u3cNGP61MdtwGTqZA0MreSaDybji8')
        assertPlaylist(u'https://www.youtube.com/playlist?list=PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC')
        assertPlaylist(u'https://www.youtube.com/watch?v=AV6J6_AeFEQ&playnext=1&list=PL4023E734DA416012') #668
        self.assertFalse('youtube:playlist' in self.matching_ies(u'PLtS2H6bU1M'))

    def test_youtube_matching(self):
        self.assertTrue(YoutubeIE.suitable(u'PLtS2H6bU1M'))
        self.assertFalse(YoutubeIE.suitable(u'https://www.youtube.com/watch?v=AV6J6_AeFEQ&playnext=1&list=PL4023E734DA416012')) #668
        self.assertMatch('http://youtu.be/BaW_jenozKc', ['youtube'])
        self.assertMatch('http://www.youtube.com/v/BaW_jenozKc', ['youtube'])
        self.assertMatch('https://youtube.googleapis.com/v/BaW_jenozKc', ['youtube'])

    def test_youtube_channel_matching(self):
        assertChannel = lambda url: self.assertMatch(url, ['youtube:channel'])
        assertChannel('https://www.youtube.com/channel/HCtnHdj3df7iM')
        assertChannel('https://www.youtube.com/channel/HCtnHdj3df7iM?feature=gb_ch_rec')
        assertChannel('https://www.youtube.com/channel/HCtnHdj3df7iM/videos')

    def test_youtube_user_matching(self):
        self.assertMatch('www.youtube.com/NASAgovVideo/videos', ['youtube:user'])

    def test_youtube_feeds(self):
        self.assertMatch('https://www.youtube.com/feed/watch_later', ['youtube:watch_later'])
        self.assertMatch('https://www.youtube.com/feed/subscriptions', ['youtube:subscriptions'])
        self.assertMatch('https://www.youtube.com/feed/recommended', ['youtube:recommended'])
        self.assertMatch('https://www.youtube.com/my_favorites', ['youtube:favorites'])

    def test_youtube_show_matching(self):
        self.assertMatch('http://www.youtube.com/show/airdisasters', ['youtube:show'])

    def test_justin_tv_channelid_matching(self):
        self.assertTrue(JustinTVIE.suitable(u"justin.tv/vanillatv"))
        self.assertTrue(JustinTVIE.suitable(u"twitch.tv/vanillatv"))
        self.assertTrue(JustinTVIE.suitable(u"www.justin.tv/vanillatv"))
        self.assertTrue(JustinTVIE.suitable(u"www.twitch.tv/vanillatv"))
        self.assertTrue(JustinTVIE.suitable(u"http://www.justin.tv/vanillatv"))
        self.assertTrue(JustinTVIE.suitable(u"http://www.twitch.tv/vanillatv"))
        self.assertTrue(JustinTVIE.suitable(u"http://www.justin.tv/vanillatv/"))
        self.assertTrue(JustinTVIE.suitable(u"http://www.twitch.tv/vanillatv/"))

    def test_justintv_videoid_matching(self):
        self.assertTrue(JustinTVIE.suitable(u"http://www.twitch.tv/vanillatv/b/328087483"))

    def test_justin_tv_chapterid_matching(self):
        self.assertTrue(JustinTVIE.suitable(u"http://www.twitch.tv/tsm_theoddone/c/2349361"))

    def test_youtube_extract(self):
        assertExtractId = lambda url, id: self.assertEqual(YoutubeIE()._extract_id(url), id)
        assertExtractId('http://www.youtube.com/watch?&v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('https://www.youtube.com/watch?&v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('https://www.youtube.com/watch?feature=player_embedded&v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('https://www.youtube.com/watch_popup?v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('http://www.youtube.com/watch?v=BaW_jenozKcsharePLED17F32AD9753930', 'BaW_jenozKc')
        assertExtractId('BaW_jenozKc', 'BaW_jenozKc')

    def test_no_duplicates(self):
        ies = gen_extractors()
        for tc in get_testcases():
            url = tc['url']
            for ie in ies:
                if type(ie).__name__ in ['GenericIE', tc['name'] + 'IE']:
                    self.assertTrue(ie.suitable(url), '%s should match URL %r' % (type(ie).__name__, url))
                else:
                    self.assertFalse(ie.suitable(url), '%s should not match URL %r' % (type(ie).__name__, url))

    def test_keywords(self):
        self.assertMatch(':ytsubs', ['youtube:subscriptions'])
        self.assertMatch(':ytsubscriptions', ['youtube:subscriptions'])
        self.assertMatch(':thedailyshow', ['ComedyCentral'])
        self.assertMatch(':tds', ['ComedyCentral'])
        self.assertMatch(':colbertreport', ['ComedyCentral'])
        self.assertMatch(':cr', ['ComedyCentral'])


if __name__ == '__main__':
    unittest.main()
