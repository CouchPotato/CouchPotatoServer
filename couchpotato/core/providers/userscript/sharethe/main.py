from couchpotato.core.providers.userscript.base import UserscriptBase


class ShareThe(UserscriptBase):

    includes = ['http://*.sharethe.tv/movies/*', 'http://sharethe.tv/movies/*']

#CouchPotato['sharethe.tv'] = (function(){
#
#    function isMovie(){
#        var pattern = /movies\/[^/]+\/?$/;
#        matched = location.href.match(pattern);
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
#        var html = document.getElementsByTagName('html')[0].innerHTML;
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
