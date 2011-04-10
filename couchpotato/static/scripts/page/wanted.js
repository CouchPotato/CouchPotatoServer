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
			m.fireEvent('injected');
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
		self.addEvent('injected', self.afterInject.bind(self))
	},

	create: function(){
		var self = this;

		self.el = new Element('div.movie').adopt(
			self.data_container = new Element('div.data', {
				'tween': {
					duration: 400,
					transition: 'quint:in:out'
				}
			}).adopt(
				self.thumbnail = File.Select.single('poster', self.data.library.files),
				self.info_container = new Element('div.info').adopt(
					self.title = new Element('div.title', {
						'text': self.getTitle()
					}),
					self.year = new Element('div.year', {
						'text': self.data.library.year || 'Unknown'
					}),
					self.rating = new Element('div.rating', {
						'text': self.data.library.rating
					}),
					self.description = new Element('div.description', {
						'text': self.data.library.plot
					}),
					self.quality = new Element('div.quality', {
						'text': self.profile.get('label')
					})
				),
				self.actions = new Element('div.actions').adopt(
					self.action_imdb = new Movie.Action.IMDB(self),
					self.action_edit = new Movie.Action.Edit(self),
					self.action_refresh = new Movie.Action.Refresh(self),
					self.action_delete = new Movie.Action.Delete(self)
				)
			)
		);

		if(!self.data.library.rating)
			self.rating.hide();

	},

	afterInject: function(){
		var self = this;

		var height = self.getHeight();
		self.el.setStyle('height', height);
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

	slide: function(direction){
		var self = this;

		if(direction == 'in'){
			self.el.addEvent('outerClick', self.slide.bind(self, 'out'))
			self.data_container.tween('left', 0, self.getWidth());
		}
		else {
			self.el.removeEvents('outerClick')
			self.data_container.tween('left', self.getWidth(), 0);
		}
	},

	getHeight: function(){
		var self = this;

		if(!self.height)
			self.height = self.data_container.getCoordinates().height;

		return self.height;
	},

	getWidth: function(){
		var self = this;

		if(!self.width)
			self.width = self.data_container.getCoordinates().width;

		return self.width;
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
				new Element('div.form').adopt(
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
		}

		self.movie.slide('in');
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
					'text': 'Delete movie',
					'events': {
						'click': self.del.bind(self)
					}
				})
			).inject(self.movie, 'top')
		}

		self.movie.slide('in');

	},

	hideConfirm: function(e){
		var self = this;
		(e).stop();

		self.movie.slide('out');
	},

	del: function(e){
		(e).stop()
		var self = this;

		var movie = $(self.movie);

		self.chain(
			function(){
				$(movie).mask().addClass('loading')
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
						})
						movie.tween('height', 0)
					}
				})
			}
		);

		self.callChain();

	}

})
