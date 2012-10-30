Page.Wanted = new Class({

	Extends: PageBase,

	name: 'wanted',
	title: 'Gimmy gimmy gimmy!',

	indexAction: function(param){
		var self = this;

		if(!self.wanted){

			self.manual_search = new Element('a', {
				'title': 'Force a search for the full wanted list',
				'text': 'Search all wanted',
				'events':{
					'click': self.doFullSearch.bind(self, true)
				}
			});

			// Wanted movies
			self.wanted = new MovieList({
				'identifier': 'wanted',
				'status': 'active',
				'actions': MovieActions,
				'add_new': true,
				'menu': [self.manual_search],
				'on_empty_element': App.createUserscriptButtons().addClass('empty_wanted')
			});
			$(self.wanted).inject(self.el);

			// Check if search is in progress
			self.startProgressInterval();
		}

	},

	doFullSearch: function(full){
		var self = this;

		if(!self.search_in_progress){

			Api.request('searcher.full_search');
			self.startProgressInterval();

		}

	},

	startProgressInterval: function(){
		var self = this;

		var start_text = self.manual_search.get('text');
		self.progress_interval = setInterval(function(){
			Api.request('searcher.progress', {
				'onComplete': function(json){
					self.search_in_progress = true;
					if(!json.progress){
						clearInterval(self.progress_interval);
						self.search_in_progress = false;
						self.manual_search.set('text', start_text);
					}
					else {
						var progress = json.progress;
						self.manual_search.set('text', 'Searching.. (' + (((progress.total-progress.to_go)/progress.total)*100).round() + '%)');
					}
				}
			})
		}, 1000);

	}

});

var MovieActions = {};
window.addEvent('domready', function(){

	MovieActions.Wanted = {
		'IMDB': IMDBAction
		,'Trailer': TrailerAction
		,'Releases': ReleaseAction
		,'Edit': new Class({

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

		,'Refresh': new Class({

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

		})

		,'Delete': new Class({

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

		})
	};

	MovieActions.Snatched = {
		'IMDB': IMDBAction
		,'Delete': MovieActions.Wanted.Delete
	};

	MovieActions.Done = {
		'IMDB': IMDBAction
		,'Edit': MovieActions.Wanted.Edit
		,'Trailer': TrailerAction
		,'Files': new Class({

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

		})
		,'Delete': MovieActions.Wanted.Delete
	};

})