from couchpotato.core.providers.extension.base import ExtensionBase


class WHiWA(ExtensionBase):

    includes = ['http://whiwa.net/stats/movie/*']

#CouchPotato['whiwa.net'] = (function(){
#
#    function isMovie(){
#        var pattern = /[^/]+\/?$/;
#        var html = document.getElementsByTagName('h3')[0].innerHTML
#        var matched = location.href.match(pattern);
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
#        var html = document.getElementsByTagName('h3')[0].innerHTML;
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
