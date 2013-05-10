var MovieAction = new Class({

	class_name: 'action icon2',

	initialize: function(movie){
		var self = this;
		self.movie = movie;

		self.create();
		if(self.el)
			self.el.addClass(self.class_name)
	},

	create: function(){},

	disable: function(){
		this.el.addClass('disable')
	},

	enable: function(){
		this.el.removeClass('disable')
	},

	createMask: function(){
		var self = this;
		self.mask = new Element('div.mask', {
			'styles': {
				'z-index': '1'
			}
		}).inject(self.movie, 'top').fade('hide');
		//self.positionMask();
	},

	positionMask: function(){
		var self = this,
			movie = $(self.movie),
			s = movie.getSize()

		return;

		return self.mask.setStyles({
			'width': s.x,
			'height': s.y
		}).position({
			'relativeTo': movie
		})
	},

	toElement: function(){
		return this.el || null
	}

});

var MA = {};

MA.IMDB = new Class({

	Extends: MovieAction,
	id: null,

	create: function(){
		var self = this;

		self.id = self.movie.get('identifier');

		self.el = new Element('a.imdb', {
			'title': 'Go to the IMDB page of ' + self.movie.getTitle(),
			'href': 'http://www.imdb.com/title/'+self.id+'/',
			'target': '_blank'
		});

		if(!self.id) self.disable();
	}

});

MA.Release = new Class({

	Extends: MovieAction,

	create: function(){
		var self = this;

		self.el = new Element('a.releases.download', {
			'title': 'Show the releases that are available for ' + self.movie.getTitle(),
			'events': {
				'click': self.show.bind(self)
			}
		});

		if(self.movie.data.releases.length == 0)
			self.el.hide()
		else
			self.showHelper();

	},

	createReleases: function(){
		var self = this;

		if(!self.options_container){
			self.options_container = new Element('div.options').grab(
				self.release_container = new Element('div.releases.table')
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
			).inject(self.release_container)

			self.movie.data.releases.sortBy('-info.score').each(function(release){

				var status = Status.get(release.status_id),
					quality = Quality.getProfile(release.quality_id) || {},
					info = release.info,
					provider = self.get(release, 'provider') + (release.info['provider_extra'] ? self.get(release, 'provider_extra') : '');
				release.status = status;

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
				new Element('div', {
					'class': 'item '+status.identifier,
					'id': 'release_'+release.id
				}).adopt(
					new Element('span.name', {'text': release_name, 'title': release_name}),
					new Element('span.status', {'text': status.identifier, 'class': 'release_status '+status.identifier}),
					new Element('span.quality', {'text': quality.get('label') || 'n/a'}),
					new Element('span.size', {'text': release.info['size'] ? Math.floor(self.get(release, 'size')) : 'n/a'}),
					new Element('span.age', {'text': self.get(release, 'age')}),
					new Element('span.score', {'text': self.get(release, 'score')}),
					new Element('span.provider', { 'text': provider, 'title': provider }),
					release.info['detail_url'] ? new Element('a.info.icon2', {
						'href': release.info['detail_url'],
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
								this.getParent('.item').toggleClass('ignored')
							}
						}
					})
				).inject(self.release_container)

				if(status.identifier == 'ignored' || status.identifier == 'failed' || status.identifier == 'snatched'){
					if(!self.last_release || (self.last_release && self.last_release.status.identifier != 'snatched' && status.identifier == 'snatched'))
						self.last_release = release;
				}
				else if(!self.next_release && status.identifier == 'available'){
					self.next_release = release;
				}
			});

			if(self.last_release){
				self.release_container.getElement('#release_'+self.last_release.id).addClass('last_release');
			}

			if(self.next_release){
				self.release_container.getElement('#release_'+self.next_release.id).addClass('next_release');
			}

			if(self.next_release || (self.last_release && ['ignored', 'failed'].indexOf(self.last_release.status.identifier) === false)){
				
				self.trynext_container = new Element('div.buttons.try_container').inject(self.release_container, 'top');

				self.trynext_container.adopt(
					new Element('span.or', {
						'text': 'This movie is snatched, if anything went wrong, download'
					}),
					self.last_release ? new Element('a.button.orange', {
						'text': 'the same release again',
						'events': {
							'click': self.trySameRelease.bind(self)
						}
					}) : null,
					self.next_release && self.last_release ? new Element('span.or', {
						'text': ','
					}) : null,
					self.next_release ? [new Element('a.button.green', {
						'text': self.last_release ? 'another release' : 'the best release',
						'events': {
							'click': self.tryNextRelease.bind(self)
						}
					}),
					new Element('span.or', {
						'text': 'or pick one below'
					})] : null
				)
			}

		}

	},

	show: function(e){
		var self = this;
		if(e)
			(e).preventDefault();

		self.createReleases();
		self.options_container.inject(self.movie, 'top');
		self.movie.slide('in', self.options_container);
	},

	showHelper: function(e){
		var self = this;
		if(e)
			(e).preventDefault();

		self.createReleases();

		if(self.next_release || (self.last_release && ['ignored', 'failed'].indexOf(self.last_release.status.identifier) === false)){

			self.trynext_container = new Element('div.buttons.trynext').inject(self.movie.info_container);

			self.trynext_container.adopt(
				self.next_release ? [new Element('a.icon2.readd', {
					'text': self.last_release ? 'Download another release' : 'Download the best release',
					'events': {
						'click': self.tryNextRelease.bind(self)
					}
				}),
				new Element('a.icon2.download', {
					'text': 'pick one yourself',
					'events': {
						'click': function(){
							self.movie.quality.fireEvent('click');
						}
					}
				})] : null,
				new Element('a.icon2.completed', {
					'text': 'mark this movie done',
					'events': {
						'click': function(){
							Api.request('movie.delete', {
								'data': {
									'id': self.movie.get('id'),
									'delete_from': 'wanted'
								},
								'onComplete': function(){
									var movie = $(self.movie);
									movie.set('tween', {
										'duration': 300,
										'onComplete': function(){
											self.movie.destroy()
										}
									});
									movie.tween('height', 0);
								}
							});
						}
					}
				})
			)
		}

	},

	get: function(release, type){
		return release.info[type] || 'n/a'
	},

	download: function(release){
		var self = this;

		var release_el = self.release_container.getElement('#release_'+release.id),
			icon = release_el.getElement('.download.icon2');

		self.movie.busy(true);

		Api.request('release.download', {
			'data': {
				'id': release.id
			},
			'onComplete': function(json){
				self.movie.busy(false);

				if(json.success)
					icon.addClass('completed');
				else
					icon.addClass('attention').set('title', 'Something went wrong when downloading, please check logs.');
			}
		});
	},

	ignore: function(release){
		var self = this;

		Api.request('release.ignore', {
			'data': {
				'id': release.id
			}
		})

	},

	tryNextRelease: function(movie_id){
		var self = this;

		self.createReleases();

		if(self.last_release)
			self.ignore(self.last_release);

		if(self.next_release)
			self.download(self.next_release);

	},

	trySameRelease: function(movie_id){
		var self = this;

		if(self.last_release)
			self.download(self.last_release);

	}

});

MA.Trailer = new Class({

	Extends: MovieAction,
	id: null,

	create: function(){
		var self = this;

		self.el = new Element('a.trailer', {
			'title': 'Watch the trailer of ' + self.movie.getTitle(),
			'events': {
				'click': self.watch.bind(self)
			}
		});

	},

	watch: function(offset){
		var self = this;

		var data_url = 'http://gdata.youtube.com/feeds/videos?vq="{title}" {year} trailer&max-results=1&alt=json-in-script&orderby=relevance&sortorder=descending&format=5&fmt=18'
		var url = data_url.substitute({
				'title': encodeURI(self.movie.getTitle()),
				'year': self.movie.get('year'),
				'offset': offset || 1
			}),
			size = $(self.movie).getSize(),
			height = (size.x/16)*9,
			id = 'trailer-'+randomString();

		self.player_container = new Element('div[id='+id+']');
		self.container = new Element('div.hide.trailer_container')
			.adopt(self.player_container)
			.inject($(self.movie), 'top');

		self.container.setStyle('height', 0);
		self.container.removeClass('hide');

		self.close_button = new Element('a.hide.hide_trailer', {
			'text': 'Hide trailer',
			'events': {
				'click': self.stop.bind(self)
			}
		}).inject(self.movie);

		self.container.setStyle('height', height);
		$(self.movie).setStyle('height', height);

		new Request.JSONP({
			'url': url,
			'onComplete': function(json){
				var video_url = json.feed.entry[0].id.$t.split('/'),
					video_id = video_url[video_url.length-1];

				self.player = new YT.Player(id, {
					'height': height,
					'width': size.x,
					'videoId': video_id,
					'playerVars': {
						'autoplay': 1,
						'showsearch': 0,
						'wmode': 'transparent',
						'iv_load_policy': 3
					}
				});

				self.close_button.removeClass('hide');

				var quality_set = false;
				var change_quality = function(state){
					if(!quality_set && (state.data == 1 || state.data || 2)){
						try {
							self.player.setPlaybackQuality('hd720');
							quality_set = true;
						}
						catch(e){

						}
					}
				}
				self.player.addEventListener('onStateChange', change_quality);

			}
		}).send()

	},

	stop: function(){
		var self = this;

		self.player.stopVideo();
		self.container.addClass('hide');
		self.close_button.addClass('hide');
		$(self.movie).setStyle('height', null);

		setTimeout(function(){
			self.container.destroy()
			self.close_button.destroy();
		}, 1800)
	}


});

MA.Edit = new Class({

	Extends: MovieAction,

	create: function(){
		var self = this;

		self.el = new Element('a.edit', {
			'title': 'Change movie information, like title and quality.',
			'events': {
				'click': self.editMovie.bind(self)
			}
		});

	},

	editMovie: function(e){
		var self = this;
		(e).preventDefault();

		if(!self.options_container){
			self.options_container = new Element('div.options').adopt(
				new Element('div.form').adopt(
					self.title_select = new Element('select', {
						'name': 'title'
					}),
					self.profile_select = new Element('select', {
						'name': 'profile'
					}),
					new Element('a.button.edit', {
						'text': 'Save & Search',
						'events': {
							'click': self.save.bind(self)
						}
					})
				)
			).inject(self.movie, 'top');

			Array.each(self.movie.data.library.titles, function(alt){
				new Element('option', {
					'text': alt.title
				}).inject(self.title_select);

				if(alt['default'])
					self.title_select.set('value', alt.title);
			});


			Quality.getActiveProfiles().each(function(profile){

				var profile_id = profile.id ? profile.id : profile.data.id;

				new Element('option', {
					'value': profile_id,
					'text': profile.label ? profile.label : profile.data.label
				}).inject(self.profile_select);

				if(self.movie.profile && self.movie.profile.data && self.movie.profile.data.id == profile_id)
					self.profile_select.set('value', profile_id);
			});

		}

		self.movie.slide('in', self.options_container);
	},

	save: function(e){
		(e).preventDefault();
		var self = this;

		Api.request('movie.edit', {
			'data': {
				'id': self.movie.get('id'),
				'default_title': self.title_select.get('value'),
				'profile_id': self.profile_select.get('value')
			},
			'useSpinner': true,
			'spinnerTarget': $(self.movie),
			'onComplete': function(){
				self.movie.quality.set('text', self.profile_select.getSelected()[0].get('text'));
				self.movie.title.set('text', self.title_select.getSelected()[0].get('text'));
			}
		});

		self.movie.slide('out');
	}

})

MA.Refresh = new Class({

	Extends: MovieAction,

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

		Api.request('movie.refresh', {
			'data': {
				'id': self.movie.get('id')
			}
		});
	}

});

MA.Readd = new Class({

	Extends: MovieAction,

	create: function(){
		var self = this;

		var movie_done = Status.get(self.movie.data.status_id).identifier == 'done';
		if(!movie_done)
			var snatched = self.movie.data.releases.filter(function(release){
				return release.status && (release.status.identifier == 'snatched' || release.status.identifier == 'downloaded' || release.status.identifier == 'done');
			}).length;

		if(movie_done || snatched && snatched > 0)
			self.el = new Element('a.readd', {
				'title': 'Readd the movie and mark all previous snatched/downloaded as ignored',
				'events': {
					'click': self.doReadd.bind(self)
				}
			});

	},

	doReadd: function(e){
		var self = this;
		(e).preventDefault();

		Api.request('movie.add', {
			'data': {
				'identifier': self.movie.get('identifier'),
				'ignore_previous': 1
			}
		});
	}

});

MA.Delete = new Class({

	Extends: MovieAction,

	Implements: [Chain],

	create: function(){
		var self = this;

		self.el = new Element('a.delete', {
			'title': 'Remove the movie from this CP list',
			'events': {
				'click': self.showConfirm.bind(self)
			}
		});

	},

	showConfirm: function(e){
		var self = this;
		(e).preventDefault();

		if(!self.delete_container){
			self.delete_container = new Element('div.buttons.delete_container').adopt(
				new Element('a.cancel', {
					'text': 'Cancel',
					'events': {
						'click': self.hideConfirm.bind(self)
					}
				}),
				new Element('span.or', {
					'text': 'or'
				}),
				new Element('a.button.delete', {
					'text': 'Delete ' + self.movie.title.get('text'),
					'events': {
						'click': self.del.bind(self)
					}
				})
			).inject(self.movie, 'top');
		}

		self.movie.slide('in', self.delete_container);

	},

	hideConfirm: function(e){
		var self = this;
		(e).preventDefault();

		self.movie.slide('out');
	},

	del: function(e){
		(e).preventDefault();
		var self = this;

		var movie = $(self.movie);

		self.chain(
			function(){
				self.callChain();
			},
			function(){
				Api.request('movie.delete', {
					'data': {
						'id': self.movie.get('id'),
						'delete_from': self.movie.list.options.identifier
					},
					'onComplete': function(){
						movie.set('tween', {
							'duration': 300,
							'onComplete': function(){
								self.movie.destroy()
							}
						});
						movie.tween('height', 0);
					}
				});
			}
		);

		self.callChain();

	}

});

MA.Files = new Class({

	Extends: MovieAction,

	create: function(){
		var self = this;

		self.el = new Element('a.directory', {
			'title': 'Available files',
			'events': {
				'click': self.showFiles.bind(self)
			}
		});

	},

	showFiles: function(e){
		var self = this;
		(e).preventDefault();

		if(!self.options_container){
			self.options_container = new Element('div.options').adopt(
				self.files_container = new Element('div.files.table')
			).inject(self.movie, 'top');

			// Header
			new Element('div.item.head').adopt(
				new Element('span.name', {'text': 'File'}),
				new Element('span.type', {'text': 'Type'}),
				new Element('span.is_available', {'text': 'Available'})
			).inject(self.files_container)

			Array.each(self.movie.data.releases, function(release){

				var rel = new Element('div.release').inject(self.files_container);

				Array.each(release.files, function(file){
					new Element('div.file.item').adopt(
						new Element('span.name', {'text': file.path}),
						new Element('span.type', {'text': File.Type.get(file.type_id).name}),
						new Element('span.available', {'text': file.available})
					).inject(rel)
				});
			});

		}

		self.movie.slide('in', self.options_container);
	},

});