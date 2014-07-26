var Episode = new Class({

    Extends: BlockBase,

    action: {},

    initialize: function(show, data){
        var self = this;

        self.show = show;
        self.data = data;

        self.el = new Element('div.item');
        self.el_actions = new Element('div.actions');

        self.create();
    },

    create: function(){
        var self = this;

        self.el.set('id', 'episode_'+self.data._id);

        self.el.adopt(
            new Element('span.episode', {'text': (self.data.info.number || 0)}),
            new Element('span.name', {'text': self.getTitle()}),
            new Element('span.firstaired', {'text': self.data.info.firstaired})
        );

        self.el_actions.inject(self.el);

        if(self.data.identifiers && self.data.identifiers.imdb) {
            new Element('a.imdb.icon2', {
                'title': 'Go to the IMDB page of ' + self.show.getTitle(),
                'href': 'http://www.imdb.com/title/' + self.data.identifiers.imdb + '/',
                'target': '_blank'
            }).inject(self.el_actions);
        }

        new Element('a.refresh.icon2', {
            'title': 'Refresh the episode info and do a forced search',
            'events': {
                'click': self.doRefresh.bind(self)
            }
        }).inject(self.el_actions);
    },

    getTitle: function(){
        var self = this;

        var title = '';

        if(self.data.info.titles && self.data.info.titles.length > 0) {
            title = self.data.info.titles[0];
        } else {
            title = 'Episode ' + self.data.info.number;
        }

        return title;
    },

    doRefresh: function(e) {
        var self = this;

        Api.request('media.refresh', {
            'data': {
                'id': self.data._id
            }
        });
    }
});