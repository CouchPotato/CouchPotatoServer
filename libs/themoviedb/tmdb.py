#!/usr/bin/env python
#-*- coding:utf-8 -*-
#author:doganaydin /// forked from dbr/Ben
#project:themoviedb
#repository:http://github.com/doganaydin/themoviedb
#license: LGPLv2 http://www.gnu.org/licenses/lgpl.html

"""An interface to the themoviedb.org API"""

__author__ = "doganaydin"
__version__ = "0.5"


config = {}

def configure(api_key):
    config['apikey'] = api_key
    config['urls'] = {}
    config['urls']['movie.search'] = "http://api.themoviedb.org/2.1/Movie.search/en/xml/%(apikey)s/%%s" % (config)
    config['urls']['movie.getInfo'] = "http://api.themoviedb.org/2.1/Movie.getInfo/en/xml/%(apikey)s/%%s" % (config)
    config['urls']['media.getInfo'] = "http://api.themoviedb.org/2.1/Media.getInfo/en/xml/%(apikey)s/%%s/%%s" % (config)
    config['urls']['imdb.lookUp'] = "http://api.themoviedb.org/2.1/Movie.imdbLookup/en/xml/%(apikey)s/%%s" % (config)
    config['urls']['movie.browse'] = "http://api.themoviedb.org/2.1/Movie.browse/en-US/xml/%(apikey)s?%%s" % (config)

import os, struct, urllib, urllib2, xml.etree.cElementTree as ElementTree

class TmdBaseError(Exception):
    pass

class TmdNoResults(TmdBaseError):
    pass

class TmdHttpError(TmdBaseError):
    pass

class TmdXmlError(TmdBaseError):
    pass

class TmdConfigError(TmdBaseError):
    pass

def opensubtitleHashFile(name):
    """Hashes a file using OpenSubtitle's method.
    > In natural language it calculates: size + 64bit chksum of the first and
    > last 64k (even if they overlap because the file is smaller than 128k).
    A slightly more Pythonic version of the Python solution on..
    http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
    """
    longlongformat = 'q'
    bytesize = struct.calcsize(longlongformat)

    f = open(name, "rb")

    filesize = os.path.getsize(name)
    fhash = filesize

    if filesize < 65536 * 2:
       raise ValueError("File size must be larger than %s bytes (is %s)" % (65536 * 2, filesize))

    for x in range(65536 / bytesize):
        buf = f.read(bytesize)
        (l_value,) = struct.unpack(longlongformat, buf)
        fhash += l_value
        fhash = fhash & 0xFFFFFFFFFFFFFFFF # to remain as 64bit number

    f.seek(max(0, filesize - 65536), 0)
    for x in range(65536 / bytesize):
        buf = f.read(bytesize)
        (l_value,) = struct.unpack(longlongformat, buf)
        fhash += l_value
        fhash = fhash & 0xFFFFFFFFFFFFFFFF

    f.close()
    return  "%016x" % fhash

class XmlHandler:
    """Deals with retrieval of XML files from API"""
    def __init__(self, url):
        self.url = url

    def _grabUrl(self, url):
        try:
            urlhandle = urllib2.urlopen(url)
        except IOError, errormsg:
            raise TmdHttpError(errormsg)
        if urlhandle.code >= 400:
            raise TmdHttpError("HTTP status code was %d" % urlhandle.code)
        return urlhandle.read()

    def getEt(self):
        xml = self._grabUrl(self.url)
        try:
            et = ElementTree.fromstring(xml)
        except SyntaxError, errormsg:
            raise TmdXmlError(errormsg)
        return et

class SearchResults(list):
    """Stores a list of Movie's that matched the search"""
    def __repr__(self):
        return "<Search results: %s>" % (list.__repr__(self))

class MovieResult(dict):
    """A dict containing the information about a specific search result"""
    def __repr__(self):
        return "<MovieResult: %s (%s)>" % (self.get("name"), self.get("released"))

    def info(self):
        """Performs a MovieDb.getMovieInfo search on the current id, returns
        a Movie object
        """
        cur_id = self['id']
        info = MovieDb().getMovieInfo(cur_id)
        return info

class Movie(dict):
    """A dict containing the information about the film"""
    def __repr__(self):
        return "<MovieResult: %s (%s)>" % (self.get("name"), self.get("released"))

class Categories(dict):
    """Stores category information"""
    def set(self, category_et):
        """Takes an elementtree Element ('category') and stores the url,
        using the type and name as the dict key.
        For example:
       <category type="genre" url="http://themoviedb.org/encyclopedia/category/80" name="Crime"/>
        ..becomes:
        categories['genre']['Crime'] = 'http://themoviedb.org/encyclopedia/category/80'
        """
        _type = category_et.get("type")
        name = category_et.get("name")
        url = category_et.get("url")
        self.setdefault(_type, {})[name] = url
        self[_type][name] = url

class Studios(dict):
    """Stores category information"""
    def set(self, studio_et):
        """Takes an elementtree Element ('studio') and stores the url,
        using the name as the dict key.
        For example:
       <studio url="http://www.themoviedb.org/encyclopedia/company/20" name="Miramax Films"/>
        ..becomes:
        studios['name'] = 'http://www.themoviedb.org/encyclopedia/company/20'
        """
        name = studio_et.get("name")
        url = studio_et.get("url")
        self[name] = url

class Countries(dict):
    """Stores country information"""
    def set(self, country_et):
        """Takes an elementtree Element ('country') and stores the url,
        using the name and code as the dict key.
        For example:
       <country url="http://www.themoviedb.org/encyclopedia/country/223" name="United States of America" code="US"/>
        ..becomes:
        countries['code']['name'] = 'http://www.themoviedb.org/encyclopedia/country/223'
        """
        code = country_et.get("code")
        name = country_et.get("name")
        url = country_et.get("url")
        self.setdefault(code, {})[name] = url

class Image(dict):
    """Stores image information for a single poster/backdrop (includes
    multiple sizes)
    """
    def __init__(self, _id, _type, size, url):
        self['id'] = _id
        self['type'] = _type

    def largest(self):
        for csize in ["original", "mid", "cover", "thumb"]:
            if csize in self:
                return csize

    def __repr__(self):
        return "<Image (%s for ID %s)>" % (self['type'], self['id'])

class ImagesList(list):
    """Stores a list of Images, and functions to filter "only posters" etc"""
    def set(self, image_et):
        """Takes an elementtree Element ('image') and stores the url,
        along with the type, id and size.
        Is a list containing each image as a dictionary (which includes the
        various sizes)
        For example:
        <image type="poster" size="original" url="http://images.themoviedb.org/posters/4181/67926_sin-city-02-color_122_207lo.jpg" id="4181"/>
        ..becomes:
        images[0] = {'id':4181', 'type': 'poster', 'original': 'http://images.themov...'}
        """
        _type = image_et.get("type")
        _id = image_et.get("id")
        size = image_et.get("size")
        url = image_et.get("url")
        cur = self.find_by('id', _id)
        if len(cur) == 0:
            nimg = Image(_id = _id, _type = _type, size = size, url = url)
            self.append(nimg)
        elif len(cur) == 1:
            cur[0][size] = url
        else:
            raise ValueError("Found more than one poster with id %s, this should never happen" % (_id))

    def find_by(self, key, value):
        ret = []
        for cur in self:
            if cur[key] == value:
                ret.append(cur)
        return ret

    @property
    def posters(self):
        return self.find_by('type', 'poster')

    @property
    def backdrops(self):
        return self.find_by('type', 'backdrop')

class CrewRoleList(dict):
    """Stores a list of roles, such as director, actor etc
    >>> import tmdb
    >>> tmdb.getMovieInfo(550)['cast'].keys()[:5]
    ['casting', 'producer', 'author', 'sound editor', 'actor']
    """
    pass

class CrewList(list):
    """Stores list of crew in specific role
    >>> import tmdb
    >>> tmdb.getMovieInfo(550)['cast']['author']
    [<author (id 7468): Chuck Palahniuk>, <author (id 7469): Jim Uhls>]
    """
    pass

class Person(dict):
    """Stores information about a specific member of cast"""
    def __init__(self, job, _id, name, character, url):
        self['job'] = job
        self['id'] = _id
        self['name'] = name
        self['character'] = character
        self['url'] = url

    def __repr__(self):
        if self['character'] is None or self['character'] == "":
            return "<%(job)s (id %(id)s): %(name)s>" % self
        else:
            return "<%(job)s (id %(id)s): %(name)s (as %(character)s)>" % self

class MovieDb:
    """Main interface to www.themoviedb.com
    The search() method searches for the film by title.
    The getMovieInfo() method retrieves information about a specific movie using themoviedb id.
    """
    def _parseSearchResults(self, movie_element):
        cur_movie = MovieResult()
        cur_images = ImagesList()
        for item in movie_element.getchildren():
                if item.tag.lower() == "images":
                    for subitem in item.getchildren():
                        cur_images.set(subitem)
                else:
                    cur_movie[item.tag] = item.text
        cur_movie['images'] = cur_images
        return cur_movie

    def _parseMovie(self, movie_element):
        cur_movie = Movie()
        cur_categories = Categories()
        cur_studios = Studios()
        cur_countries = Countries()
        cur_images = ImagesList()
        cur_cast = CrewRoleList()
        for item in movie_element.getchildren():
            if item.tag.lower() == "categories":
                for subitem in item.getchildren():
                    cur_categories.set(subitem)
            elif item.tag.lower() == "studios":
                for subitem in item.getchildren():
                    cur_studios.set(subitem)
            elif item.tag.lower() == "countries":
                for subitem in item.getchildren():
                    cur_countries.set(subitem)
            elif item.tag.lower() == "images":
                for subitem in item.getchildren():
                    cur_images.set(subitem)
            elif item.tag.lower() == "cast":
                for subitem in item.getchildren():
                    job = subitem.get("job").lower()
                    p = Person(
                        job = job,
                        _id = subitem.get("id"),
                        name = subitem.get("name"),
                        character = subitem.get("character"),
                        url = subitem.get("url"),
                    )
                    cur_cast.setdefault(job, CrewList()).append(p)
            else:
                cur_movie[item.tag] = item.text

        cur_movie['categories'] = cur_categories
        cur_movie['studios'] = cur_studios
        cur_movie['countries'] = cur_countries
        cur_movie['images'] = cur_images
        cur_movie['cast'] = cur_cast
        return cur_movie

    def search(self, title):
        """Searches for a film by its title.
        Returns SearchResults (a list) containing all matches (Movie instances)
        """
        title = urllib.quote(title.encode("utf-8"))
        url = config['urls']['movie.search'] % (title)
        etree = XmlHandler(url).getEt()
        search_results = SearchResults()
        for cur_result in etree.find("movies").findall("movie"):
            cur_movie = self._parseSearchResults(cur_result)
            search_results.append(cur_movie)
        return search_results

    def getMovieInfo(self, id):
        """Returns movie info by it's TheMovieDb ID.
        Returns a Movie instance
        """
        url = config['urls']['movie.getInfo'] % (id)
        etree = XmlHandler(url).getEt()
        moviesTree = etree.find("movies").findall("movie")

        if len(moviesTree) == 0:
            raise TmdNoResults("No results for id %s" % id)
        return self._parseMovie(moviesTree[0])

    def mediaGetInfo(self, hash, size):
        """Used to retrieve specific information about a movie but instead of
        passing a TMDb ID, you pass a file hash and filesize in bytes
        """
        url = config['urls']['media.getInfo'] % (hash, size)
        etree = XmlHandler(url).getEt()
        moviesTree = etree.find("movies").findall("movie")
        if len(moviesTree) == 0:
            raise TmdNoResults("No results for hash %s" % hash)
        return [self._parseMovie(x) for x in moviesTree]

    def imdbLookup(self, id = 0, title = False):
        if not config.get('apikey'):
            raise TmdConfigError("API Key not set")
        if id > 0:
            url = config['urls']['imdb.lookUp'] % (id)
        else:
            _imdb_id = self.search(title)[0]["imdb_id"]
            url = config['urls']['imdb.lookUp'] % (_imdb_id)
        etree = XmlHandler(url).getEt()
        lookup_results = SearchResults()
        for cur_lookup in etree.find("movies").findall("movie"):
            cur_movie = self._parseSearchResults(cur_lookup)
            lookup_results.append(cur_movie)
        return lookup_results

class Browse:

    def __init__(self, params = {}):
        """
            tmdb.Browse(params)
            default params = {"order_by":"release","order":"desc"}
            params = {"query":"some query","release_max":"1991",...}
            all posible parameters = http://api.themoviedb.org/2.1/methods/Movie.browse    
        """
        if "order_by" not in params:
            params.update({"order_by":"release"})
        if "order" not in params:
            params.update({"order":"desc"})

        self.params = urllib.urlencode(params)
        self.movie = self.look(self.params)

    def look(self, look_for):
        url = config['urls']['movie.browse'] % (look_for)
        etree = XmlHandler(url).getEt()
        look_results = SearchResults()
        for cur_lookup in etree.find("movies").findall("movie"):
            cur_movie = self._parseSearchResults(cur_lookup)
            look_results.append(cur_movie)
        return look_results

    def _parseSearchResults(self, movie_element):
        cur_movie = MovieResult()
        cur_images = ImagesList()
        for item in movie_element.getchildren():
                if item.tag.lower() == "images":
                    for subitem in item.getchildren():
                        cur_images.set(subitem)
                else:
                    cur_movie[item.tag] = item.text
        cur_movie['images'] = cur_images
        return cur_movie

    def getTotal(self):
        return len(self.movie)

    def getRating(self, i):
        return self.movie[i]["rating"]

    def getVotes(self, i):
        return self.movie[i]["votes"]

    def getName(self, i):
        return self.movie[i]["name"]

    def getLanguage(self, i):
        return self.movie[i]["language"]

    def getCertification(self, i):
        return self.movie[i]["certification"]

    def getUrl(self, i):
        return self.movie[i]["url"]

    def getOverview(self, i):
        return self.movie[i]["overview"]

    def getPopularity(self, i):
        return self.movie[i]["popularity"]

    def getOriginalName(self, i):
        return self.movie[i]["original_name"]

    def getLastModified(self, i):
        return self.movie[i]["last_modified_at"]

    def getImdbId(self, i):
        return self.movie[i]["imdb_id"]

    def getReleased(self, i):
        return self.movie[i]["released"]

    def getScore(self, i):
        return self.movie[i]["score"]

    def getAdult(self, i):
        return self.movie[i]["adult"]

    def getVersion(self, i):
        return self.movie[i]["version"]

    def getTranslated(self, i):
        return self.movie[i]["translated"]

    def getType(self, i):
        return self.movie[i]["type"]

    def getId(self, i):
        return self.movie[i]["id"]

    def getAlternativeName(self, i):
        return self.movie[i]["alternative_name"]

    def getPoster(self, i, size):
        if size == "thumb" or size == "t":
            return self.movie[i]["images"][0]["thumb"]
        elif size == "cover" or size == "c":
            return self.movie[i]["images"][0]["cover"]
        else:
            return self.movie[i]["images"][0]["mid"]

    def getBackdrop(self, i, size):
        if size == "poster" or size == "p":
            return self.movie[i]["images"][1]["poster"]
        else:
            return self.movie[i]["images"][1]["thumb"]



# Shortcuts for tmdb search method
# using:
#   movie = tmdb.tmdb("Sin City")
#   print movie.getRating -> 7.0
class tmdb:

    def __init__(self, name):
        """Convenience wrapper for MovieDb.search - so you can do..
        >>> import tmdb
        >>> movie = tmdb.tmdb("Fight Club")
        >>> ranking = movie.getRanking() or votes = movie.getVotes()
        <Search results: [<MovieResult: Fight Club (1999-09-16)>]>
        """
        mdb = MovieDb()
        self.movie = mdb.search(name)

    def getTotal(self):
        return len(self.movie)

    def getRating(self, i):
        return self.movie[i]["rating"]

    def getVotes(self, i):
        return self.movie[i]["votes"]

    def getName(self, i):
        return self.movie[i]["name"]

    def getLanguage(self, i):
        return self.movie[i]["language"]

    def getCertification(self, i):
        return self.movie[i]["certification"]

    def getUrl(self, i):
        return self.movie[i]["url"]

    def getOverview(self, i):
        return self.movie[i]["overview"]

    def getPopularity(self, i):
        return self.movie[i]["popularity"]

    def getOriginalName(self, i):
        return self.movie[i]["original_name"]

    def getLastModified(self, i):
        return self.movie[i]["last_modified_at"]

    def getImdbId(self, i):
        return self.movie[i]["imdb_id"]

    def getReleased(self, i):
        return self.movie[i]["released"]

    def getScore(self, i):
        return self.movie[i]["score"]

    def getAdult(self, i):
        return self.movie[i]["adult"]

    def getVersion(self, i):
        return self.movie[i]["version"]

    def getTranslated(self, i):
        return self.movie[i]["translated"]

    def getType(self, i):
        return self.movie[i]["type"]

    def getId(self, i):
        return self.movie[i]["id"]

    def getAlternativeName(self, i):
        return self.movie[i]["alternative_name"]

    def getPoster(self, i, size):
        if size == "thumb" or size == "t":
            return self.movie[i]["images"][0]["thumb"]
        elif size == "cover" or size == "c":
            return self.movie[i]["images"][0]["cover"]
        else:
            return self.movie[i]["images"][0]["mid"]

    def getBackdrop(self, i, size):
        if size == "poster" or size == "p":
            return self.movie[i]["images"][1]["poster"]
        else:
            return self.movie[i]["images"][1]["thumb"]

# Shortcuts for imdb lookup method
# using:
#   movie = tmdb.imdb("Sin City")
#   print movie.getRating -> 7.0         
class imdb:

    def __init__(self, id = 0, title = False):
        # get first movie if result=0
        """Convenience wrapper for MovieDb.search - so you can do..
        >>> import tmdb
        >>> movie = tmdb.imdb(title="Fight Club") # or movie = tmdb.imdb(id=imdb_id)
        >>> ranking = movie.getRanking() or votes = movie.getVotes()
        <Search results: [<MovieResult: Fight Club (1999-09-16)>]>
        """
        self.id = id
        self.title = title
        self.mdb = MovieDb()
        self.movie = self.mdb.imdbLookup(self.id, self.title)

    def getTotal(self):
        return len(self.movie)

    def getRuntime(self, i):
        return self.movie[i]["runtime"]

    def getCategories(self):
        from xml.dom.minidom import parse
        adres = config['urls']['imdb.lookUp'] % self.getImdbId()
        d = parse(urllib2.urlopen(adres))
        s = d.getElementsByTagName("categories")
        ds = []
        for i in range(len(s[0].childNodes)):
            if i % 2 > 0:
                ds.append(s[0].childNodes[i].getAttribute("name"))
        return ds

    def getRating(self, i):
        return self.movie[i]["rating"]

    def getVotes(self, i):
        return self.movie[i]["votes"]

    def getName(self, i):
        return self.movie[i]["name"]

    def getLanguage(self, i):
        return self.movie[i]["language"]

    def getCertification(self, i):
        return self.movie[i]["certification"]

    def getUrl(self, i):
        return self.movie[i]["url"]

    def getOverview(self, i):
        return self.movie[i]["overview"]

    def getPopularity(self, i):
        return self.movie[i]["popularity"]

    def getOriginalName(self, i):
        return self.movie[i]["original_name"]

    def getLastModified(self, i):
        return self.movie[i]["last_modified_at"]

    def getImdbId(self, i):
        return self.movie[i]["imdb_id"]

    def getReleased(self, i):
        return self.movie[i]["released"]

    def getAdult(self, i):
        return self.movie[i]["adult"]

    def getVersion(self, i):
        return self.movie[i]["version"]

    def getTranslated(self, i):
        return self.movie[i]["translated"]

    def getType(self, i):
        return self.movie[i]["type"]

    def getId(self, i):
        return self.movie[i]["id"]

    def getAlternativeName(self, i):
        return self.movie[i]["alternative_name"]

    def getPoster(self, i, size):
        poster = []
        if size == "thumb" or size == "t":
            _size = "thumb"
        elif size == "cover" or size == "c":
            _size = "cover"
        else:
            _size = "mid"
        for a in self.movie[i]["images"]:
            if a["type"] == "poster":
                poster.append(a[_size])
        return poster
        del poster

    def getBackdrop(self, i, size):
        backdrop = []
        if size == "thumb" or size == "t":
            _size = "thumb"
        elif size == "cover" or size == "c":
            _size = "cover"
        else:
            _size = "mid"
        for a in self.movie[i]["images"]:
            if a["type"] == "backdrop":
                backdrop.append(a[_size])
        return backdrop
        del backdrop

def imdbLookup(id = 0, title = False):
    """Convenience wrapper for Imdb.Lookup - so you can do..
    >>> import tmdb
    >>> tmdb.imdbLookup("Fight Club")
    <Search results: [<MovieResult: Fight Club (1999-09-16)>]>
    """
    mdb = MovieDb()
    return mdb.imdbLookup(id, title)

def search(name):
    """Convenience wrapper for MovieDb.search - so you can do..
    >>> import tmdb
    >>> tmdb.search("Fight Club")
    <Search results: [<MovieResult: Fight Club (1999-09-16)>]>
    """
    mdb = MovieDb()
    return mdb.search(name)

def getMovieInfo(id):
    """Convenience wrapper for MovieDb.search - so you can do..
    >>> import tmdb
    >>> tmdb.getMovieInfo(187)
    <MovieResult: Sin City (2005-04-01)>
    """
    mdb = MovieDb()
    return mdb.getMovieInfo(id)

def mediaGetInfo(hash, size):
    """Convenience wrapper for MovieDb.mediaGetInfo - so you can do..

    >>> import tmdb
    >>> tmdb.mediaGetInfo('907172e7fe51ba57', size = 742086656)[0]
    <MovieResult: Sin City (2005-04-01)>
    """
    mdb = MovieDb()
    return mdb.mediaGetInfo(hash, size)

def searchByHashingFile(filename):
    """Searches for the specified file using the OpenSubtitle hashing method
    """
    return mediaGetInfo(opensubtitleHashFile(filename), os.path.size(filename))

def main():
    results = search("Fight Club")
    searchResult = results[0]
    movie = getMovieInfo(searchResult['id'])
    print movie['name']

    print "Producers:"
    for prodr in movie['cast']['producer']:
        print " " * 4, prodr['name']
    print movie['images']
    for genreName in movie['categories']['genre']:
        print "%s (%s)" % (genreName, movie['categories']['genre'][genreName])

if __name__ == '__main__':
    main()
