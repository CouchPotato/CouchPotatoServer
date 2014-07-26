var Episode = new Class({

    Extends: BlockBase,

    action: {},

    initialize: function(show, data){
        var self = this;

        self.show = show;
        self.data = data;

        self.profile = self.show.profile;

        self.el = new Element('div.item.data');
        self.el_actions = new Element('div.episode-actions');

        self.create();
    },

    create: function(){
        var self = this;

        self.el.set('id', 'episode_'+self.data._id);

        self.el.adopt(
            new Element('span.episode', {'text': (self.data.info.number || 0)}),
            new Element('span.name', {'text': self.getTitle()}),
            new Element('span.firstaired', {'text': self.data.info.firstaired}),

            self.quality = new Element('span.quality')
        );

        self.el_actions.inject(self.el);

        // imdb
        if(self.data.identifiers && self.data.identifiers.imdb) {
            new Element('a.imdb.icon2', {
                'title': 'Go to the IMDB page of ' + self.show.getTitle(),
                'href': 'http://www.imdb.com/title/' + self.data.identifiers.imdb + '/',
                'target': '_blank'
            }).inject(self.el_actions);
        }

        // refresh
        new Element('a.refresh.icon2', {
            'title': 'Refresh the episode info and do a forced search',
            'events': {
                'click': self.doRefresh.bind(self)
            }
        }).inject(self.el_actions);

        // Add profile
        if(self.profile.data) {
            self.profile.getTypes().each(function(type){
                var q = self.addQuality(type.get('quality'), type.get('3d'));

                if((type.finish == true || type.get('finish')) && !q.hasClass('finish')){
                    q.addClass('finish');
                    q.set('title', q.get('title') + ' Will finish searching for this movie if this quality is found.')
                }
            });
        }

        // Add releases
        self.updateReleases();
    },

    updateReleases: function(){
        var self = this;
        if(!self.data.releases || self.data.releases.length == 0) return;

        self.data.releases.each(function(release){

            var q = self.quality.getElement('.q_'+ release.quality+(release.is_3d ? '.is_3d' : ':not(.is_3d)')),
                status = release.status;

            if(!q && (status == 'snatched' || status == 'seeding' || status == 'done'))
                q = self.addQuality(release.quality, release.is_3d || false);

            if (q && !q.hasClass(status)){
                q.addClass(status);
                q.set('title', (q.get('title') ? q.get('title') : '') + ' status: '+ status)
            }

        });
    },

    addQuality: function(quality, is_3d){
        var self = this,
            q = Quality.getQuality(quality);

        return new Element('span', {
            'text': q.label + (is_3d ? ' 3D' : ''),
            'class': 'q_'+q.identifier + (is_3d ? ' is_3d' : ''),
            'title': ''
        }).inject(self.quality);
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