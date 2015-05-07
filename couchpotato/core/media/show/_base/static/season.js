var Season = new Class({

    Extends: BlockBase,

    action: {},

    initialize: function(show, options, data){
        var self = this;
        self.setOptions(options);

        self.show = show;
        self.options = options;
        self.data = data;

        self.profile = self.show.profile;

        self.el = new Element('div.item.season').adopt(
            self.detail = new Element('div.item.data')
        );

        self.create();
    },

    create: function(){
        var self = this;

        self.detail.set('id', 'season_'+self.data._id);

        self.detail.adopt(
            new Element('span.name', {'text': self.getTitle()}),

            self.quality = new Element('span.quality', {
                'events': {
                    'click': function(e){
                        var releases = self.detail.getElement('.item-actions .releases');

                        if(releases.isVisible())
                            releases.fireEvent('click', [e])
                    }
                }
            }),
            self.actions = new Element('div.item-actions')
        );

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

        Object.each(self.options.actions, function(action, key){
            self.action[key.toLowerCase()] = action = new self.options.actions[key](self);
            if(action.el)
                self.actions.adopt(action)
        });
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

        if(self.data.info.number) {
            title = 'Season ' + self.data.info.number;
        } else {
            // Season 0 / Specials
            title = 'Specials';
        }

        return title;
    },

    getIdentifier: function(){
        var self = this;

        try {
            return self.get('identifiers').imdb;
        }
        catch (e){ }

        return self.get('imdb');
    },

    get: function(attr){
        return this.data[attr] || this.data.info[attr]
    }
});