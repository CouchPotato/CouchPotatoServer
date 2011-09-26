from couchpotato.core.providers.extension.base import ExtensionBase


class Trakt(ExtensionBase):

    includes = ['http://trakt.tv/movie/*', 'http://*.trakt.tv/movie/*']
    excludes = ['http://trakt.tv/movie/*/*', 'http://*.trakt.tv/movie/*/*']

#CouchPotato['trakt.tv'] = (function(){
#
#    var imdb_input = null;
#    var year_input = null;
#
#    function isMovie(){
#        imdb_input = document.getElementById("meta-imdb-id");
#        year_input = document.getElementById("meta-year");
#        return (null != imdb_input) && (null != year_input);
#    }
#
#    function getId(){
#        return imdb_input.value.substr(2);
#    }
#
#    function getYear(){
#        return year_input.value;
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
