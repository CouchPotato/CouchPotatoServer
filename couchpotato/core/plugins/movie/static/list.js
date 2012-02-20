var MovieList = new Class({

	Implements: [Options],

	options: {
		navigation: false,
		limit: 50
	},

	movies: [],
	letters: {},
	filter: {
		'startswith': null,
		'search': null
	},

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.offset = 0;

		self.el = new Element('div.movies').adopt(
			self.movie_list = new Element('div'),
			self.load_more = new Element('a.load_more', {
				'events': {
					'click': self.loadMore.bind(self)
				}
			})
		);
		self.getMovies();
	},

	create: function(){
		var self = this;

		// Create the alphabet nav
		if(self.options.navigation)
			self.createNavigation();

		self.movie_list.addEvents({
			'mouseenter:relay(.movie)': function(e, el){
				el.addClass('hover');
			},
			'mouseleave:relay(.movie)': function(e, el){
				el.removeClass('hover');
			}
		});

		self.scrollspy = new ScrollSpy({
			min: function(){
				var c = self.load_more.getCoordinates()
				return c.top - window.document.getSize().y - 300
			},
			onEnter: self.loadMore.bind(self)
		});

		self.created = true;
	},

	addMovies: function(movies){
		var self = this;

		if(!self.created) self.create();

		// do scrollspy
		if(movies.length < self.options.limit){
			self.load_more.hide();
			self.scrollspy.stop();
		}

		Object.each(movies, function(info){

			// Attach proper actions
			var a = self.options.actions
			var actions = a[info.status.identifier.capitalize()] || a.Wanted || {};

			var m = new Movie(self, {
				'actions': actions
			}, info);
			$(m).inject(self.movie_list);
			m.fireEvent('injected');

		});

	},

	createNavigation: function(){
		var self = this;
		var chars = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ';

		self.navigation = new Element('div.alph_nav').adopt(
			self.alpha = new Element('ul.inlay', {
				'events': {
					'click:relay(li)': function(e, el){
						self.movie_list.empty()
						self.activateLetter(el.get('data-letter'))
						self.getMovies()
					}
				}
			}),
			self.search_input = new Element('input.inlay', {
				'placeholder': 'Search',
				'events': {
					'keyup': self.search.bind(self),
					'change': self.search.bind(self)
				}
			})/*,
			self.view = new Element('ul.inlay').adopt(
				new Element('li.list'),
				new Element('li.thumbnails'),
				new Element('li.text')
			)*/
		).inject(self.el, 'top');

		// All
		self.letters['all'] = new Element('li.letter_all.available.active', {
			'text': 'ALL',
		}).inject(self.alpha);

		// Chars
		chars.split('').each(function(c){
			self.letters[c] = new Element('li', {
				'text': c,
				'class': 'letter_'+c,
				'data-letter': c
			}).inject(self.alpha);
		});

		// Get available chars and highlight
		Api.request('movie.available_chars', {
			'data': Object.merge({
				'status': self.options.status
			}, self.filter),
			'onComplete': function(json){

				json.chars.split('').each(function(c){
					self.letters[c.capitalize()].addClass('available')
				})

			}
		});

		self.nav_scrollspy = new ScrollSpy({
			min: 10,
			onEnter: function(){
				self.navigation.addClass('float')
			},
			onLeave: function(){
				self.navigation.removeClass('float')
			}
		});

	},

	reset: function(){
		var self = this;

		self.navigation.getElements('.active').removeClass('active')
		self.offset = 0;
		self.load_more.show();
		self.scrollspy.start();
	},

	activateLetter: function(letter){
		var self = this;

		self.reset()

		self.letters[letter || 'all'].addClass('active');
		self.filter.starts_with = letter;

	},

	search: function(){
		var self = this;

		if(self.search_timer) clearTimeout(self.search_timer);
		self.search_timer = (function(){
			var search_value = self.search_input.get('value');
			if (search_value == self.last_search_value) return

			self.reset()

			self.activateLetter();
			self.filter.search = search_value;

			self.movie_list.empty();
			self.getMovies();

			self.last_search_value = search_value;

		}).delay(250);

	},

	update: function(){
		var self = this;

		self.getMovies();
	},

	getMovies: function(){
		var self = this;

		if(self.scrollspy) self.scrollspy.stop();
		self.load_more.set('text', 'loading...');
		Api.request('movie.list', {
			'data': Object.merge({
				'status': self.options.status,
				'limit_offset': self.options.limit + ',' + self.offset
			}, self.filter),
			'onComplete': function(json){
				self.store(json.movies);
				self.addMovies(json.movies);
				self.load_more.set('text', 'load more movies');
				if(self.scrollspy) self.scrollspy.start();
			}
		});
	},

	loadMore: function(){
		var self = this;
		if(self.offset >= self.options.limit)
			self.getMovies()
	},

	store: function(movies){
		var self = this;

		self.offset += movies.length;

	},

	toElement: function(){
		return this.el;
	}

});