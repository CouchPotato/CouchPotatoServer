var MovieList = new Class({

	Implements: [Options],

	options: {
		navigation: false
	},

	movies: [],
	letters: {},

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.el = new Element('div.movies');
		self.getMovies();
	},

	create: function(){
		var self = this;

		self.el.empty();

		// Create the alphabet nav
		if(self.options.navigation)
			self.createNavigation();

		Object.each(self.movies, function(info){

			// Attach proper actions
			var a = self.options.actions
			var actions = a[info.status.identifier.capitalize()] || a.Wanted || {};

			var m = new Movie(self, {
				'actions': actions
			}, info);
			$(m).inject(self.el);
			m.fireEvent('injected');

			if(self.options.navigation){
				var first_char = m.getTitle().substr(0, 1);
				self.activateLetter(first_char);
			}
		});

		self.el.addEvents({
			'mouseenter:relay(.movie)': function(e, el){
				el.addClass('hover');
			},
			'mouseleave:relay(.movie)': function(e, el){
				el.removeClass('hover');
			}
		});
	},

	createNavigation: function(){
		var self = this;
		var chars = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ';

		self.navigation = new Element('div.alph_nav').adopt(
			self.alpha = new Element('ul.inlay'),
			self.input = new Element('input.inlay'),
			self.view = new Element('ul.inlay').adopt(
				new Element('li.list'),
				new Element('li.thumbnails'),
				new Element('li.text')
			)
		).inject(this.el, 'top');

		chars.split('').each(function(c){
			self.letters[c] = new Element('li', {
				'text': c,
				'class': 'letter_'+c
			}).inject(self.alpha);
		});

	},

	activateLetter: function(letter){
		this.letters[letter].addClass('active');
	},

	update: function(){
		var self = this;

		self.getMovies();
	},

	getMovies: function(){
		var self = this;

		Api.request('movie.list', {
			'data': {
				'status': self.options.status
			},
			'onComplete': function(json){
				self.store(json.movies);
				self.create();
			}
		});
	},

	store: function(movies){
		var self = this;

		self.movies = movies;
	},

	toElement: function(){
		return this.el;
	}

});