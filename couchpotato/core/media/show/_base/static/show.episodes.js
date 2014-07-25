var Episodes = new Class({
    initialize: function(show) {
        var self = this;

        self.show = show;
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

        self.show.slide('in', self.container);
    },

    createEpisodes: function() {
        var self = this;

        self.data.seasons.sort(function(a, b) {
            var an = a.info.number || 0;
            var bn = b.info.number || 0;

            if(an < bn)
                return -1;

            if(an > bn)
                return 1;

            return 0;
        });

        self.data.seasons.each(function(season) {
            season['el'] = new Element('div', {
                'class': 'item head',
                'id': 'season_'+season._id
            }).adopt(
                new Element('span.name', {'text': 'Season ' + (season.info.number || 0)})
            ).inject(self.episodes_container);

            season.episodes.sort(function(a, b) {
                var an = a.info.number || 0;
                var bn = b.info.number || 0;

                if(an < bn)
                    return -1;

                if(an > bn)
                    return 1;

                return 0;
            });

            season.episodes.each(function(episode) {
                var title = '';

                if(episode.info.titles && episode.info.titles.length > 0) {
                    title = episode.info.titles[0];
                }

                episode['el'] = new Element('div', {
                    'class': 'item',
                    'id': 'episode_'+episode._id
                }).adopt(
                    new Element('span.episode', {'text': (episode.info.number || 0)}),
                    new Element('span.name', {'text': title}),
                    new Element('span.firstaired', {'text': episode.info.firstaired})
                ).inject(self.episodes_container);

                episode['el_actions'] = new Element('div.actions').inject(episode['el']);

                if(episode.identifiers && episode.identifiers.imdb) {
                    new Element('a.imdb.icon2', {
                        'title': 'Go to the IMDB page of ' + self.show.getTitle(),
                        'href': 'http://www.imdb.com/title/' + episode.identifiers.imdb + '/',
                        'target': '_blank'
                    }).inject(episode['el_actions']);
                }

                new Element('a.refresh.icon2', {
                    'title': 'Refresh the episode info and do a forced search',
                    'events': {
                        'click': self.doRefresh.bind(self)
                    }
                }).inject(episode['el_actions']);
            });
        });
    },

    doRefresh: function() {

    }
});