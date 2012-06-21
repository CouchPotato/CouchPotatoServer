Page.Queue = new Class({

	Extends: PageBase,

	name: 'Queue',
	title: 'Movies waiting!',

	indexAction: function(param){
		var self = this;

		if(!self.snatched){

			// Snatched movies
			self.snatched = new MovieList({
				'identifier': 'wanted',
				'status': 'snatched',
				'actions': MovieActions,
				'add_new': true
			});
			$(self.snatched).inject(self.el);
		}

	}

});

var MovieActions = {};
window.addEvent('domready', function(){

	MovieActions.snatched = {
		'IMDB': IMDBAction
		,'ALLOCINE': ALLOCINEAction
		,'SENSACINE': SENSACINEAction
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
						new Element('option', {
							'value': profile.id ? profile.id : profile.data.id,
							'text': profile.label ? profile.label : profile.data.label
						}).inject(self.profile_select);

						if(self.movie.profile)
							self.profile_select.set('value', self.movie.profile.data.id);
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
					self.delete_container = new Element('div.delete_container').adopt(
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


	MovieActions.Snatched = {
		'IMDB': IMDBAction
		,'ALLOCINE': ALLOCINEAction
		,'SENSACINE': SENSACINEAction
		,'Trailer': TrailerAction
		,'Delete': MovieActions.snatched.Delete
	};

	MovieActions.Done = {
		'IMDB': IMDBAction
		,'ALLOCINE': ALLOCINEAction
		,'SENSACINE': SENSACINEAction
		,'Edit': MovieActions.snatched.Edit
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
		,'Delete': MovieActions.snatched.Delete
	};

})
