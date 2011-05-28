var MovieList = new Class({

	Implements: [Options],

	options: {
		navigation: true
	},

	movies: [],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.el = new Element('div.movies');
		self.getMovies();
	},

	create: function(){
		var self = this;

		// Create the alphabet nav
		if(self.options.navigation)
			self.createNavigation();

		Object.each(self.movies, function(info){
			var m = new Movie(self, {
				'actions': self.options.actions
			}, info);
			$(m).inject(self.el);
			m.fireEvent('injected');
		});

		self.el.addEvents({
			'mouseenter:relay(.movie)': function(e, el){
				el.addClass('hover')
			},
			'mouseleave:relay(.movie)': function(e, el){
				el.removeClass('hover')
			}
		});
	},

	createNavigation: function(){
		var self = this;
		var chars = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ';
		var selected = 'Z';

		self.navigation = new Element('div.alph_nav').adopt(
			self.alpha = new Element('ul.inlay'),
			self.input = new Element('input.inlay'),
			self.view = new Element('ul.inlay').adopt(
				new Element('li.list'),
				new Element('li.thumbnails'),
				new Element('li.text')
			)
		).inject(this.el, 'top')

		chars.split('').each(function(c){
			new Element('li', {
				'text': c,
				'class': c == selected ? 'selected' : ''
			}).inject(self.alpha)
		})

	},

	getMovies: function(status, onComplete){
		var self = this

		if(self.movies.length == 0)
			Api.request('movie.list', {
				'data': {
					'status': self.options.status
				},
				'onComplete': function(json){
					self.store(json.movies);
					self.create();
				}
			})
		else
			self.list()
	},

	store: function(movies){
		var self = this;

		self.movies = movies;
	},

	toElement: function(){
		return this.el;
	}

});