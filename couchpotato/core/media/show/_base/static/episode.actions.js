var EpisodeAction = new Class({

    Implements: [Options],

    class_name: 'item-action icon2',

    initialize: function(episode, options){
        var self = this;
        self.setOptions(options);

        self.show = episode.show;
        self.episode = episode;

        self.create();
        if(self.el)
            self.el.addClass(self.class_name)
    },

    create: function(){},

    disable: function(){
        if(this.el)
            this.el.addClass('disable')
    },

    enable: function(){
        if(this.el)
            this.el.removeClass('disable')
    },

    getTitle: function(){
        var self = this;

        try {
            return self.show.getTitle();
        }
        catch(e){
            try {
                return self.show.original_title ? self.show.original_title : self.show.titles[0];
            }
            catch(e){
                return 'Unknown';
            }
        }
    },

    get: function(key){
        var self = this;
        try {
            return self.show.get(key)
        }
        catch(e){
            return self.show[key]
        }
    },

    createMask: function(){
        var self = this;
        self.mask = new Element('div.mask', {
            'styles': {
                'z-index': '1'
            }
        }).inject(self.show, 'top').fade('hide');
    },

    toElement: function(){
        return this.el || null
    }

});

var EA = {};

EA.IMDB = new Class({

    Extends: EpisodeAction,
    id: null,

    create: function(){
        var self = this;

        self.id = self.show.getIdentifier ? self.show.getIdentifier() : self.get('imdb');

        self.el = new Element('a.imdb', {
            'title': 'Go to the IMDB page of ' + self.getTitle(),
            'href': 'http://www.imdb.com/title/'+self.id+'/',
            'target': '_blank'
        });

        if(!self.id) self.disable();
    }

});

EA.Release = new Class({

    Extends: EpisodeAction,

    create: function(){
        var self = this;

        self.el = new Element('a.releases.download', {
            'title': 'Show the releases that are available for ' + self.getTitle(),
            'events': {
                'click': self.toggle.bind(self)
            }
        });

        self.options = new Element('div.episode-options').inject(self.episode.el);

        if(!self.episode.data.releases || self.episode.data.releases.length == 0)
            self.el.hide();
        else
            self.showHelper();

        App.on('show.searcher.ended', function(notification){
            if(self.show.data._id != notification.data._id) return;

            self.releases = null;
            if(self.options_container){
                self.options_container.destroy();
                self.options_container = null;
            }
        });

    },

    toggle: function(e){
        var self = this;

        if(self.options && self.options.hasClass('expanded')) {
            self.close();
        } else {
            self.open();
        }
    },

    open: function(e){
        var self = this;

        if(e)
            (e).preventDefault();

        self.createReleases();

    },

    close: function(e) {
        var self = this;

        if(e)
            (e).preventDefault();

        self.options.setStyle('height', 0)
                    .removeClass('expanded');
    },

    createReleases: function(){
        var self = this;

        if(!self.releases_table){
            self.options.adopt(
                self.releases_table = new Element('div.releases.table')
            );

            // Header
            new Element('div.item.head').adopt(
                new Element('span.name', {'text': 'Release name'}),
                new Element('span.status', {'text': 'Status'}),
                new Element('span.quality', {'text': 'Quality'}),
                new Element('span.size', {'text': 'Size'}),
                new Element('span.age', {'text': 'Age'}),
                new Element('span.score', {'text': 'Score'}),
                new Element('span.provider', {'text': 'Provider'})
            ).inject(self.releases_table);

            if(self.episode.data.releases)
                self.episode.data.releases.each(function(release){

                    var quality = Quality.getQuality(release.quality) || {},
                        info = release.info || {},
                        provider = self.get(release, 'provider') + (info['provider_extra'] ? self.get(release, 'provider_extra') : '');

                    var release_name = self.get(release, 'name');
                    if(release.files && release.files.length > 0){
                        try {
                            var movie_file = release.files.filter(function(file){
                                var type = File.Type.get(file.type_id);
                                return type && type.identifier == 'movie'
                            }).pick();
                            release_name = movie_file.path.split(Api.getOption('path_sep')).getLast();
                        }
                        catch(e){}
                    }

                    // Create release
                    release['el'] = new Element('div', {
                        'class': 'item '+release.status,
                        'id': 'release_'+release._id
                    }).adopt(
                            new Element('span.name', {'text': release_name, 'title': release_name}),
                            new Element('span.status', {'text': release.status, 'class': 'status '+release.status}),
                            new Element('span.quality', {'text': quality.label + (release.is_3d ? ' 3D' : '') || 'n/a'}),
                            new Element('span.size', {'text': info['size'] ? Math.floor(self.get(release, 'size')) : 'n/a'}),
                            new Element('span.age', {'text': self.get(release, 'age')}),
                            new Element('span.score', {'text': self.get(release, 'score')}),
                            new Element('span.provider', { 'text': provider, 'title': provider }),
                            info['detail_url'] ? new Element('a.info.icon2', {
                                'href': info['detail_url'],
                                'target': '_blank'
                            }) : new Element('a'),
                            new Element('a.download.icon2', {
                                'events': {
                                    'click': function(e){
                                        (e).preventDefault();
                                        if(!this.hasClass('completed'))
                                            self.download(release);
                                    }
                                }
                            }),
                            new Element('a.delete.icon2', {
                                'events': {
                                    'click': function(e){
                                        (e).preventDefault();
                                        self.ignore(release);
                                    }
                                }
                            })
                        ).inject(self.releases_table);

                    if(release.status == 'ignored' || release.status == 'failed' || release.status == 'snatched'){
                        if(!self.last_release || (self.last_release && self.last_release.status != 'snatched' && release.status == 'snatched'))
                            self.last_release = release;
                    }
                    else if(!self.next_release && release.status == 'available'){
                        self.next_release = release;
                    }

                    var update_handle = function(notification) {
                        if(notification.data._id != release._id) return;

                        var q = self.show.quality.getElement('.q_' + release.quality),
                            new_status = notification.data.status;

                        release.el.set('class', 'item ' + new_status);

                        var status_el = release.el.getElement('.release_status');
                        status_el.set('class', 'release_status ' + new_status);
                        status_el.set('text', new_status);

                        if(!q && (new_status == 'snatched' || new_status == 'seeding' || new_status == 'done'))
                            q = self.addQuality(release.quality_id);

                        if(q && !q.hasClass(new_status)) {
                            q.removeClass(release.status).addClass(new_status);
                            q.set('title', q.get('title').replace(release.status, new_status));
                        }
                    };

                    App.on('release.update_status', update_handle);

                });

            if(self.last_release)
                self.releases_table.getElements('#release_'+self.last_release._id).addClass('last_release');

            if(self.next_release)
                self.releases_table.getElements('#release_'+self.next_release._id).addClass('next_release');

            if(self.next_release || (self.last_release && ['ignored', 'failed'].indexOf(self.last_release.status) === false)){

                self.trynext_container = new Element('div.buttons.try_container').inject(self.releases_table, 'top');

                var nr = self.next_release,
                    lr = self.last_release;

                self.trynext_container.adopt(
                    new Element('span.or', {
                        'text': 'If anything went wrong, download'
                    }),
                    lr ? new Element('a.button.orange', {
                        'text': 'the same release again',
                        'events': {
                            'click': function(){
                                self.download(lr);
                            }
                        }
                    }) : null,
                    nr && lr ? new Element('span.or', {
                        'text': ','
                    }) : null,
                    nr ? [new Element('a.button.green', {
                        'text': lr ? 'another release' : 'the best release',
                        'events': {
                            'click': function(){
                                self.download(nr);
                            }
                        }
                    }),
                        new Element('span.or', {
                            'text': 'or pick one below'
                        })] : null
                )
            }

            self.last_release = null;
            self.next_release = null;

            self.episode.el.addEvent('outerClick', function(){
                self.close();
            });
        }

        self.options.setStyle('height', self.releases_table.getSize().y)
                    .addClass('expanded');

    },

    showHelper: function(e){
        var self = this;
        if(e)
            (e).preventDefault();

        var has_available = false,
            has_snatched = false;

        if(self.episode.data.releases)
            self.episode.data.releases.each(function(release){
                if(has_available && has_snatched) return;

                if(['snatched', 'downloaded', 'seeding'].contains(release.status))
                    has_snatched = true;

                if(['available'].contains(release.status))
                    has_available = true;

            });

        if(has_available || has_snatched){

            self.trynext_container = new Element('div.buttons.trynext').inject(self.show.info_container);

            self.trynext_container.adopt(
                has_available ? [new Element('a.icon2.readd', {
                    'text': has_snatched ? 'Download another release' : 'Download the best release',
                    'events': {
                        'click': self.tryNextRelease.bind(self)
                    }
                }),
                    new Element('a.icon2.download', {
                        'text': 'pick one yourself',
                        'events': {
                            'click': function(){
                                self.show.quality.fireEvent('click');
                            }
                        }
                    })] : null,
                new Element('a.icon2.completed', {
                    'text': 'mark this movie done',
                    'events': {
                        'click': self.markMovieDone.bind(self)
                    }
                })
            )
        }

    },

    get: function(release, type){
        return (release.info && release.info[type] !== undefined) ? release.info[type] : 'n/a'
    },

    download: function(release){
        var self = this;

        var release_el = self.releases_table.getElement('#release_'+release._id),
            icon = release_el.getElement('.download.icon2');

        if(icon)
            icon.addClass('icon spinner').removeClass('download');

        Api.request('release.manual_download', {
            'data': {
                'id': release._id
            },
            'onComplete': function(json){
                if(icon)
                    icon.removeClass('icon spinner');

                if(json.success){
                    if(icon)
                        icon.addClass('completed');
                    release_el.getElement('.release_status').set('text', 'snatched');
                }
                else
                if(icon)
                    icon.addClass('attention').set('title', 'Something went wrong when downloading, please check logs.');
            }
        });
    },

    ignore: function(release){

        Api.request('release.ignore', {
            'data': {
                'id': release._id
            }
        })

    },

    markMovieDone: function(){
        var self = this;

        Api.request('media.delete', {
            'data': {
                'id': self.show.get('_id'),
                'delete_from': 'wanted'
            },
            'onComplete': function(){
                var movie = $(self.show);
                movie.set('tween', {
                    'duration': 300,
                    'onComplete': function(){
                        self.show.destroy()
                    }
                });
                movie.tween('height', 0);
            }
        });

    },

    tryNextRelease: function(){
        var self = this;

        Api.request('movie.searcher.try_next', {
            'data': {
                'media_id': self.show.get('_id')
            }
        });

    }

});

EA.Refresh = new Class({

    Extends: EpisodeAction,

    create: function(){
        var self = this;

        self.el = new Element('a.refresh', {
            'title': 'Refresh the movie info and do a forced search',
            'events': {
                'click': self.doRefresh.bind(self)
            }
        });

    },

    doRefresh: function(e){
        var self = this;
        (e).preventDefault();

        Api.request('media.refresh', {
            'data': {
                'id': self.episode.get('_id')
            }
        });
    }

});