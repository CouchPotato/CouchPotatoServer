var Episodes = new Class({
    initialize: function(show, options) {
        var self = this;

        self.show = show;
        self.options = options;
    },

    open: function(){
        var self = this;

        if(!self.container){
            self.container = new Element('div.options').grab(
                self.episodes_container = new Element('div.episodes.table')
            );

            self.container.inject(self.show, 'top');

            Api.request('library.tree', {
                'data': {
                    'media_id': self.show.data._id
                },
                'onComplete': function(json){
                    self.data = json.result;

                    self.createEpisodes();
                }
            });
        }

        self.show.slide('in', self.container, true);
    },

    createEpisodes: function() {
        var self = this;

        self.data.seasons.sort(self.sortSeasons);
        self.data.seasons.each(function(season) {
            self.createSeason(season);

            season.episodes.sort(self.sortEpisodes);
            season.episodes.each(function(episode) {
                self.createEpisode(episode);
            });
        });
    },

    createSeason: function(season) {
        var self = this,
            s = new Season(self.show, self.options, season);

        $(s).inject(self.episodes_container);
    },

    createEpisode: function(episode){
        var self = this,
            e = new Episode(self.show, self.options, episode);

        $(e).inject(self.episodes_container);
    },

    sortSeasons: function(a, b) {
        // Move "Specials" to the bottom of the list
        if(!a.info.number) {
            return 1;
        }

        if(!b.info.number) {
            return -1;
        }

        // Order seasons descending
        if(a.info.number < b.info.number)
            return -1;

        if(a.info.number > b.info.number)
            return 1;

        return 0;
    },

    sortEpisodes: function(a, b) {
        // Order episodes descending
        if(a.info.number <  b.info.number)
            return -1;

        if(a.info.number >  b.info.number)
            return 1;

        return 0;
    }
});