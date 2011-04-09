Page.Wanted = new Class({

	Extends: PageBase,

	name: 'wanted',
	title: 'Gimmy gimmy gimmy!',

	movies: [],

	indexAction: function(param){
		var self = this;

		self.get()
	},

	list: function(){
		var self = this;

		if(!self.movie_container)
			self.movie_container = new Element('div.movies').inject(self.el);

		self.movie_container.empty();
		Object.each(self.movies, function(info){
			var m = new Movie(self, {}, info);
			$(m).inject(self.movie_container);
		});

		self.movie_container.addEvents({
			'mouseenter:relay(.movie)': function(e, el){
				el.addClass('hover')
			},
			'mouseleave:relay(.movie)': function(e, el){
				el.removeClass('hover')
			}
		})
	},

	get: function(status, onComplete){
		var self = this

		if(self.movies.length == 0)
			Api.request('movie.list', {
				'data': {},
				'onComplete': function(json){
					self.store(json.movies);
					self.list();
				}
			})
		else
			self.list()
	},

	store: function(movies){
		var self = this;

		self.movies = movies;
	}

});

var Movie = new Class({

	Extends: BlockBase,

	initialize: function(self, options, data){
		var self = this;

		self.data = data;

		self.profile = Quality.getProfile(data.profile_id);
		self.parent(self, options);
	},

	create: function(){
		var self = this;

		self.el = new Element('div.movie').adopt(
			self.data_container = new Element('div').adopt(
				self.thumbnail = File.Select.single('poster', self.data.library.files),
				self.title = new Element('div.title', {
					'text': self.getTitle()
				}),
				self.description = new Element('div.description', {
					'text': self.data.library.plot
				}),
				self.rating = new Element('div.rating', {
					'text': self.data.library.rating || 10
				}),
				self.year = new Element('div.year', {
					'text': self.data.library.year || 'Unknown'
				}),
				self.quality = new Element('div.quality', {
					'text': self.profile.get('label')
				}),
				self.actions = new Element('div.actions').adopt(
					self.action_imdb = new Movie.Action.IMDB(self),
					self.action_edit = new Movie.Action.Edit(self),
					self.action_refresh = new Movie.Action.Refresh(self),
					self.action_delete = new Movie.Action.Delete(self)
				)
			)
		);

	},

	getTitle: function(){
		var self = this;

		var titles = self.data.library.titles;

		var title = titles.filter(function(title){
			return title['default']
		}).pop()

		if(title)
			return  title.title
		else if(titles.length > 0)
			return titles[0].title

		return 'Unknown movie'
	},

	get: function(attr){
		return this.data[attr] || this.data.library[attr]
	}

});

var MovieAction = new Class({

	class_name: 'action',

	initialize: function(movie){
		var self = this;
		self.movie = movie;

		self.create();
		self.el.addClass(self.class_name)
	},

	create: function(){},

	disable: function(){
		this.el.addClass('disable')
	},

	enable: function(){
		this.el.removeClass('disable')
	},

	toElement: function(){
		return this.el
	}

})

Movie.Action = {}

Movie.Action.Edit = new Class({

	Extends: MovieAction,

	create: function(){
		var self = this;

		self.el = new Element('a.edit', {
			'text': 'edit',
			'title': 'Refresh the movie info and do a forced search',
			'events': {
				'click': self.editMovie.bind(self)
			}
		});

	},

	editMovie: function(e){
		var self = this;
		(e).stop();

		self.optionContainer = new Element('div.options').adopt(
			$(self.movie.thumbnail).clone(),
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
		).inject(self.movie, 'top');
	},

	save: function(){
		var self = this;

		Api.request('movie.edit', {
			'data': {
				'default_title': self.title_select.get('value'),
				'profile_id': self.profile_select.get('value')
			},
			'useSpinner': true,
			'spinnerTarget': self.movie
		})
	}

})

Movie.Action.IMDB = new Class({

	Extends: MovieAction,
	id: null,

	create: function(){
		var self = this;

		self.id = self.movie.get('identifier');

		self.el = new Element('a.imdb', {
			'text': 'imdb',
			'title': 'Go to the IMDB page of ' + self.movie.getTitle(),
			'events': {
				'click': self.gotoIMDB.bind(self)
			}
		});

		if(!self.id) self.disable();
	},

	gotoIMDB: function(e){
		var self = this;
		(e).stop();

		window.open('http://www.imdb.com/title/'+self.id+'/');
	}

})

Movie.Action.Refresh = new Class({

	Extends: MovieAction,

	create: function(){
		var self = this;

		self.el = new Element('a.refresh', {
			'text': 'refresh',
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
		})
	}

})

Movie.Action.Delete = new Class({

	Extends: MovieAction,

	Implements: [Chain],

	create: function(){
		var self = this;

		self.el = new Element('a.delete', {
			'text': 'delete',
			'title': 'Remove the movie from your wanted list',
			'events': {
				'click': self.showConfirm.bind(self)
			}
		});

	},

	showConfirm: function(e){
		var self = this;
		(e).stop();

		self.mask = $(self.movie).mask({
			'destroyOnHide': true
		});

		$(self.mask).adopt(
			new Element('a.button.delete', {
				'text': 'Delete movie',
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('span', {
				'text': 'or'
			}),
			new Element('a.button.cancel', {
				'text': 'Cancel',
				'events': {
					'click': self.mask.hide.bind(self.mask)
				}
			})
		);
	},

	del: function(e){
		(e).stop()
		var self = this;

		var movie = $(self.movie);

		self.chain(
			function(){
				$(self.mask).empty().addClass('loading');
				self.callChain();
			},
			function(){
				Api.request('movie.delete', {
					'data': {
						'id': self.movie.get('id')
					},
					'onComplete': function(){
						p(movie, $(self.movie))
						movie.slide('in');
					}
				})
			}
		);

		self.callChain();

	}

})
