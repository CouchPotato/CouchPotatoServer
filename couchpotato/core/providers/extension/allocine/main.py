from couchpotato.core.providers.extension.base import ExtensionBase


class AlloCine(ExtensionBase):

    includes = ['http://www.allocine.fr/film/*']

#CouchPotato['allocine.fr'] = (function(){
#
#    function isMovie(){
#        var pattern = /fichefilm_gen_cfilm=\d+?\.html$/;
#        matched = location.href.match(pattern);
#        return null != matched;
#    }
#
#    function getId() {
#        var name = document.title.substr(0, document.title.indexOf(" -")).replace(/ /g, "+");
#        lib.search(name, getYear())
#    }
#
#    function getYear(){
#        var year = new RegExp("\\d{4}", document.title)
#        return year;
#    }
#
#    function constructor(){
#         if(isMovie()){
#            lib.osd(getId(), getYear());
#           }
#    }
#
#    return constructor;
#    
#})();
