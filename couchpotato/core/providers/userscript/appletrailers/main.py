from couchpotato.core.providers.userscript.base import UserscriptBase


class AppleTrailers(UserscriptBase):

    includes = ['http://trailers.apple.com/trailers/*']

#CouchPotato['trailers.apple.com'] = (function(){
#
#    function getId() {
#        var name = document.title.substr(0, document.title.indexOf(" -")).replace(/ /g, "+");
#        return lib.search(name, getYear())
#
#    }
#
#    function getYear(){
#        var release_date = document.getElementById("view-showtimes").parentNode.innerHTML;
#        var year = new RegExp("\\d{4}", release_date)
#
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
