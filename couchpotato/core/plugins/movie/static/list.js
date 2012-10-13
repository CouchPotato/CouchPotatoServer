var MovieList = new Class({

	Implements: [Options],

	options: {
		navigation: true,
		limit: 50,
		menu: [],
		add_new: false
	},

	movies: [],
	movies_added: {},
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

		App.addEvent('movie.added', self.movieAdded.bind(self))
		App.addEvent('movie.deleted', self.movieDeleted.bind(self))
	},

	movieDeleted: function(notification){
		var self = this;

		if(self.movies_added[notification.data.id]){
			self.movies.each(function(movie){
				if(movie.get('id') == notification.data.id){
					movie.destroy();
					delete self.movies_added[notification.data.id]
				}
			})
		}

		self.checkIfEmpty();
	},

	movieAdded: function(notification){
		var self = this;
		window.scroll(0,0);

		if(self.options.add_new && !self.movies_added[notification.data.id] && notification.data.status.identifier == self.options.status)
			self.createMovie(notification.data, 'top');

		self.checkIfEmpty();
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

	addMovies: function(movies, total){
		var self = this;

		if(!self.created) self.create();

		// do scrollspy
		if(movies.length < self.options.limit){
			self.load_more.hide();
			self.scrollspy.stop();
		}

		Object.each(movies, function(movie){
			self.createMovie(movie);
		});

		self.setCounter(total);

	},

	setCounter: function(count){
		var self = this;

		if(!self.navigation_counter) return;

		self.navigation_counter.set('text', (count || 0));

	},

	createMovie: function(movie, inject_at){
		var self = this;

		// Attach proper actions
		var a = self.options.actions,
			status = Status.get(movie.status_id);
		var actions = a[status.identifier.capitalize()] || a.Wanted || {};

		var m = new Movie(self, {
			'actions': actions,
			'view': self.current_view,
			'onSelect': self.calculateSelected.bind(self)
		}, movie);
		$(m).inject(self.movie_list, inject_at || 'bottom');
		m.fireEvent('injected');

		self.movies.include(m)
		self.movies_added[movie.id] = true;
	},

	createNavigation: function(){
		var self = this;
		var chars = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ';

		self.current_view = self.getSavedView();
		self.el.addClass(self.current_view+'_list')

		self.navigation = new Element('div.alph_nav').adopt(
			self.navigation_actions = new Element('ul.inlay.actions.reversed'),
			self.navigation_counter = new Element('span.counter[title=Total]'),
			self.navigation_alpha = new Element('ul.numbers', {
				'events': {
					'click:relay(li)': function(e, el){
						self.movie_list.empty()
						self.activateLetter(el.get('data-letter'))
						self.getMovies()
					}
				}
			}),
			self.navigation_search_input = new Element('input.inlay', {
				'placeholder': 'Search',
				'events': {
					'keyup': self.search.bind(self),
					'change': self.search.bind(self)
				}
			}),
			self.navigation_menu = new Block.Menu(self),
			self.mass_edit_form = new Element('div.mass_edit_form').adopt(
				new Element('span.select').adopt(
					self.mass_edit_select = new Element('input[type=checkbox].inlay', {
						'events': {
							'change': self.massEditToggleAll.bind(self)
						}
					}),
					self.mass_edit_selected = new Element('span.count', {'text': 0}),
					self.mass_edit_selected_label = new Element('span', {'text': 'selected'})
				),
				new Element('div.quality').adopt(
					self.mass_edit_quality = new Element('select'),
					new Element('a.button.orange', {
						'text': 'Change quality',
						'events': {
							'click': self.changeQualitySelected.bind(self)
						}
					})
				),
				new Element('div.delete').adopt(
					new Element('span[text=or]'),
					new Element('a.button.red', {
						'text': 'Delete',
						'events': {
							'click': self.deleteSelected.bind(self)
						}
					})
				),
				new Element('div.refresh').adopt(
					new Element('span[text=or]'),
					new Element('a.button.green', {
						'text': 'Refresh',
						'events': {
							'click': self.refreshSelected.bind(self)
						}
					})
				)
			)
		).inject(self.el, 'top');

		// Mass edit
		self.mass_edit_select_class = new Form.Check(self.mass_edit_select);
		Quality.getActiveProfiles().each(function(profile){
			new Element('option', {
				'value': profile.id ? profile.id : profile.data.id,
				'text': profile.label ? profile.label : profile.data.label
			}).inject(self.mass_edit_quality)
		});

		// Actions
		['mass_edit', 'thumbs', 'list'].each(function(view){
			self.navigation_actions.adopt(
				new Element('li.'+view+(self.current_view == view ? '.active' : '')+'[data-view='+view+']', {
					'events': {
						'click': function(e){
							var a = 'active';
							self.navigation_actions.getElements('.'+a).removeClass(a);
							self.changeView(this.get('data-view'));
							this.addClass(a);
						}
					}
				}).adopt(new Element('span'))
			)
		});

		// All
		self.letters['all'] = new Element('li.letter_all.available.active', {
			'text': 'ALL',
		}).inject(self.navigation_alpha);

		// Chars
		chars.split('').each(function(c){
			self.letters[c] = new Element('li', {
				'text': c,
				'class': 'letter_'+c,
				'data-letter': c
			}).inject(self.navigation_alpha);
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

		// Add menu or hide
		if (self.options.menu.length > 0)
			self.options.menu.each(function(menu_item){
				self.navigation_menu.addLink(menu_item);
			})
		else
			self.navigation_menu.hide()

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

	calculateSelected: function(){
		var self = this;

		var selected = 0,
			movies = self.movies.length;
		self.movies.each(function(movie){
			selected += movie.isSelected() ? 1 : 0
		})

		var indeterminate = selected > 0 && selected < movies,
			checked = selected == movies && selected > 0;

		self.mass_edit_select.set('indeterminate', indeterminate)

		self.mass_edit_select_class[checked ? 'check' : 'uncheck']()
		self.mass_edit_select_class.element[indeterminate ? 'addClass' : 'removeClass']('indeterminate')

		self.mass_edit_selected.set('text', selected);
	},

	deleteSelected: function(){
		var self = this;
		var ids = self.getSelectedMovies()

		var qObj = new Question('Are you sure you want to delete '+ids.length+' movie'+ (ids.length != 1 ? 's' : '') +'?', 'If you do, you won\'t be able to watch them, as they won\'t get downloaded!', [{
			'text': 'Yes, delete '+(ids.length != 1 ? 'them' : 'it'),
			'class': 'delete',
			'events': {
				'click': function(e){
					(e).preventDefault();
					this.set('text', 'Deleting..')
					Api.request('movie.delete', {
						'data': {
							'id': ids.join(','),
							'delete_from': self.options.identifier
						},
						'onSuccess': function(){
							qObj.close();

							var erase_movies = [];
							self.movies.each(function(movie){
								if (movie.isSelected()){
									$(movie).destroy()
									erase_movies.include(movie)
								}
							});

							erase_movies.each(function(movie){
								self.movies.erase(movie);

								movie.destroy()
							});

							self.calculateSelected();
						}
					});

				}
			}
		}, {
			'text': 'Cancel',
			'cancel': true
		}]);

	},

	changeQualitySelected: function(){
		var self = this;
		var ids = self.getSelectedMovies()

		Api.request('movie.edit', {
			'data': {
				'id': ids.join(','),
				'profile_id': self.mass_edit_quality.get('value')
			},
			'onSuccess': self.search.bind(self)
		});
	},

	refreshSelected: function(){
		var self = this;
		var ids = self.getSelectedMovies()

		Api.request('movie.refresh', {
			'data': {
				'id': ids.join(','),
			}
		});
	},

	getSelectedMovies: function(){
		var self = this;

		var ids = []
		self.movies.each(function(movie){
			if (movie.isSelected())
				ids.include(movie.get('id'))
		});

		return ids
	},

	massEditToggleAll: function(){
		var self = this;

		var select = self.mass_edit_select.get('checked');

		self.movies.each(function(movie){
			movie.select(select)
		});

		self.calculateSelected()
	},

	reset: function(){
		var self = this;

		self.movies = []
		self.calculateSelected()
		self.navigation_alpha.getElements('.active').removeClass('active')
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

	changeView: function(new_view){
		var self = this;

		self.movies.each(function(movie){
			movie.changeView(new_view)
		});

		self.el
			.removeClass(self.current_view+'_list')
			.addClass(new_view+'_list')

		self.current_view = new_view;
		Cookie.write(self.options.identifier+'_view', new_view, {duration: 1000});
	},

	getSavedView: function(){
		var self = this;
		return Cookie.read(self.options.identifier+'_view') || 'thumbs';
	},

	search: function(){
		var self = this;

		if(self.search_timer) clearTimeout(self.search_timer);
		self.search_timer = (function(){
			var search_value = self.navigation_search_input.get('value');
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

		self.reset();
		self.movie_list.empty();
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
				self.addMovies(json.movies, json.total);
				self.load_more.set('text', 'load more movies');
				if(self.scrollspy) self.scrollspy.start();

				self.checkIfEmpty()
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

	checkIfEmpty: function(){
		var self = this;

		var is_empty = self.movies.length == 0;

		if(is_empty && self.options.on_empty_element){
			self.el.grab(self.options.on_empty_element);

			if(self.navigation)
				self.navigation.hide();

			self.empty_element = self.options.on_empty_element;
		}
		else if(self.empty_element){
			self.empty_element.destroy();

			if(self.navigation)
				self.navigation.show();
		}

	},

	toElement: function(){
		return this.el;
	}

});