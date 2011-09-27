from couchpotato.core.providers.userscript.base import UserscriptBase


class TMDB(UserscriptBase):

    includes = ['http://www.themoviedb.org/movie/*']

#CouchPotato['themoviedb.org'] = (function(){
#
#    var obj = this;
#
#    function getId() {
#
#        name = document.title.substr(0, document.title.indexOf("TMDb")-3).replace(/ /g, "+");
#        lib.search(name, getYear())
#
#    }
#
#    function getYear(){
#        var year = document.getElementById("year").innerHTML;
#        year = year.substr(1, year.length-2);
#        return year;
#    }
#
#    function constructor(){
#        getId();
#    }
#
#    return constructor;
#
#})();
