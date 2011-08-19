Page.Wanted = new Class({

	Extends: PageBase,

	name: 'wanted',
	title: 'Gimmy gimmy gimmy!',

	indexAction: function(param){
		var self = this;

		if(!self.list){
			
			// Wanted movies
			self.wanted = new MovieList({
				'status': 'active',
				'actions': WantedActions
			});
			$(self.wanted).inject(self.el);
			App.addEvent('library.update', self.wanted.update.bind(self.wanted));
		}

	}

});

var WantedActions = {
	'IMBD': IMDBAction
	//,'releases': ReleaseAction

	,'Edit': new Class({

		Extends: MovieAction,
	
		create: function(){
			var self = this;
	
			self.el = new Element('a.edit', {
				'title': 'Refresh the movie info and do a forced search',
				'events': {
					'click': self.editMovie.bind(self)
				}
			});
	
		},
	
		editMovie: function(e){
			var self = this;
			(e).stop();
	
			if(!self.options_container){
				self.options_container = new Element('div.options').adopt(
					$(self.movie.thumbnail).clone(),
					new Element('div.form', {
						'styles': {
							'line-height': self.movie.getHeight()
						}
					}).adopt(
						self.title_select = new Element('select', {
							'name': 'title'
						}),
						self.profile_select = new Element('select', {
							'name': 'profile'
						}),
						new Element('a.button.edit', {
							'text': 'Save',
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
				});
	
				Object.each(Quality.profiles, function(profile){
					new Element('option', {
						'value': profile.id ? profile.id : profile.data.id,
						'text': profile.label ? profile.label : profile.data.label
					}).inject(self.profile_select);
					self.profile_select.set('value', self.movie.profile.get('id'));
				});
	
			}
			self.movie.slide('in');
		},
	
		save: function(e){
			(e).stop();
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

	,'Refresh': new Class({

		Extends: MovieAction,
	
		create: function(){
			var self = this;
	
			self.el = new Element('a.refresh', {
				'title': 'Refresh the movie info and do a forced search',
				'events': {
					'click': self.doSearch.bind(self)
				}
			});
	
		},
	
		doSearch: function(e){
			var self = this;
			(e).stop();
	
			Api.request('movie.refresh', {
				'data': {
					'id': self.movie.get('id')
				}
			});
		}
	
	})

	,'Delete': new Class({

		Extends: MovieAction,
	
		Implements: [Chain],
	
		create: function(){
			var self = this;
	
			self.el = new Element('a.delete', {
				'title': 'Remove the movie from your wanted list',
				'events': {
					'click': self.showConfirm.bind(self)
				}
			});
	
		},
	
		showConfirm: function(e){
			var self = this;
			(e).stop();
	
			if(!self.delete_container){
				self.delete_container = new Element('div.delete_container', {
					'styles': {
						'line-height': self.movie.getHeight()
					}
				}).adopt(
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
	
			self.movie.slide('in');
	
		},
	
		hideConfirm: function(e){
			var self = this;
			(e).stop();
	
			self.movie.slide('out');
		},
	
		del: function(e){
			(e).stop();
			var self = this;
	
			var movie = $(self.movie);
	
			self.chain(
				function(){
					$(movie).mask().addClass('loading');
					self.callChain();
				},
				function(){
					Api.request('movie.delete', {
						'data': {
							'id': self.movie.get('id')
						},
						'onComplete': function(){
							movie.set('tween', {
								'onComplete': function(){
									movie.destroy();
								}
							});
							movie.tween('height', 0);
						}
					});
				}
			);
	
			self.callChain();
	
		}

	})
};

var SnatchedActions = {
	'IMBD': IMDBAction
	,'Releases': ReleaseAction
	,'Delete': WantedActions.Delete
};