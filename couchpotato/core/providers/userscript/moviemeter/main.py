from couchpotato.core.providers.userscript.base import UserscriptBase


class MovieMeter(UserscriptBase):

    includes = ['http://*.moviemeter.nl/film/*', 'http://moviemeter.nl/film/*']

#CouchPotato['moviemeter.nl'] = (function(){
#
#    function isMovie(){
#        var pattern = /[^/]+\/?$/;
#        var html = document.getElementsByTagName('h1')[0].innerHTML
#    matched = location.href.match(pattern);
#        return null != matched;
#    }
#
#    function getId(){
#        var pattern = /imdb\.com\/title\/tt(\d+)/;
#        var html = document.getElementsByTagName('html')[0].innerHTML;
#        var imdb_id = html.match(pattern)[1];
#        return imdb_id;
#
#    }
#
#    function getYear(){
#        var pattern = /(\d+)[^\d]*$/;
#        var html = document.getElementsByTagName('h1')[0].innerHTML;
#        var year = html.match(pattern)[1];
#        return year;
#
#    }
#
#    function constructor(){
#        if(isMovie()){
#            lib.osd(getId(), getYear());
#        }
#    }
#
#    return constructor;
#
#})();
