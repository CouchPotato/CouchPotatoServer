var MovieList = new Class({

	Implements: [Events, Options],

	options: {
		navigation: true,
		limit: 50,
		load_more: true,
		loader: true,
		menu: [],
		add_new: false,
		force_view: false
	},

	movies: [],
	movies_added: {},
	total_movies: 0,
	letters: {},
	filter: null,

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.offset = 0;
		self.filter = self.options.filter || {
			'starts_with': null,
			'search': null
		};

		self.el = new Element('div.movies').adopt(
			self.title = self.options.title ? new Element('h2', {
				'text': self.options.title,
				'styles': {'display': 'none'}
			}) : null,
			self.description = self.options.description ? new Element('div.description', {
				'html': self.options.description,
				'styles': {'display': 'none'}
			}) : null,
			self.movie_list = new Element('div'),
			self.load_more = self.options.load_more ? new Element('a.load_more', {
				'events': {
					'click': self.loadMore.bind(self)
				}
			}) : null
		);

		if($(window).getSize().x <= 480 && !self.options.force_view)
			self.changeView('list');
		else
			self.changeView(self.getSavedView() || self.options.view || 'details');

		self.getMovies();

		App.on('movie.added', self.movieAdded.bind(self));
		App.on('movie.deleted', self.movieDeleted.bind(self))
	},

	movieDeleted: function(notification){
		var self = this;

		if(self.movies_added[notification.data._id]){
			self.movies.each(function(movie){
				if(movie.get('_id') == notification.data._id){
					movie.destroy();
					delete self.movies_added[notification.data._id];
					self.setCounter(self.counter_count-1);
					self.total_movies--;
				}
			})
		}

		self.checkIfEmpty();
	},

	movieAdded: function(notification){
		var self = this;

		self.fireEvent('movieAdded', notification);
		if(self.options.add_new && !self.movies_added[notification.data._id] && notification.data.status == self.options.status){
			window.scroll(0,0);
			self.createMovie(notification.data, 'top');
			self.setCounter(self.counter_count+1);

			self.checkIfEmpty();
		}
	},

	create: function(){
		var self = this;

		// Create the alphabet nav
		if(self.options.navigation)
			self.createNavigation();

		if(self.options.load_more)
			self.scrollspy = new ScrollSpy({
				min: function(){
					var c = self.load_more.getCoordinates();
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
		if(movies.length < self.options.limit && self.scrollspy){
			self.load_more.hide();
			self.scrollspy.stop();
		}

		Object.each(movies, function(movie){
			self.createMovie(movie);
		});

		self.total_movies += total;
		self.setCounter(total);

	},

	setCounter: function(count){
		var self = this;

		if(!self.navigation_counter) return;

		self.counter_count = count;
		self.navigation_counter.set('text', (count || 0) + ' movies');

		if (self.empty_message) {
			self.empty_message.destroy();
			self.empty_message = null;
		}

		if(self.total_movies && count == 0 && !self.empty_message){
			var message = (self.filter.search ? 'for "'+self.filter.search+'"' : '') +
				(self.filter.starts_with ? ' in <strong>'+self.filter.starts_with+'</strong>' : '');

			self.empty_message = new Element('.message', {
				'html': 'No movies found ' + message + '.<br/>'
			}).grab(
				new Element('a', {
					'text': 'Reset filter',
					'events': {
						'click': function(){
							self.filter = {
								'starts_with': null,
								'search': null
							};
							self.navigation_search_input.set('value', '');
							self.reset();
							self.activateLetter();
							self.getMovies(true);
							self.last_search_value = '';
						}
					}
				})
			).inject(self.movie_list);

		}

	},

	createMovie: function(movie, inject_at){
		var self = this;
		var m = new Movie(self, {
			'actions': self.options.actions,
			'view': self.current_view,
			'onSelect': self.calculateSelected.bind(self)
		}, movie);

		$(m).inject(self.movie_list, inject_at || 'bottom');

		m.fireEvent('injected');

		self.movies.include(m);
		self.movies_added[movie._id] = true;
	},

	createNavigation: function(){
		var self = this;
		var chars = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ';

		self.el.addClass('with_navigation');

		self.navigation = new Element('div.alph_nav').adopt(
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
			),
			new Element('div.menus').adopt(
				self.navigation_counter = new Element('span.counter[title=Total]'),
				self.filter_menu = new Block.Menu(self, {
					'class': 'filter'
				}),
				self.navigation_actions = new Element('ul.actions', {
					'events': {
						'click:relay(li)': function(e, el){
							var a = 'active';
							self.navigation_actions.getElements('.'+a).removeClass(a);
							self.changeView(el.get('data-view'));
							this.addClass(a);

							el.inject(el.getParent(), 'top');
							el.getSiblings().hide();
							setTimeout(function(){
								el.getSiblings().setStyle('display', null);
							}, 100)
						}
					}
				}),
				self.navigation_menu = new Block.Menu(self, {
					'class': 'extra'
				})
			)
		).inject(self.el, 'top');

		// Mass edit
		self.mass_edit_select_class = new Form.Check(self.mass_edit_select);
		Quality.getActiveProfiles().each(function(profile){
			new Element('option', {
				'value': profile.get('_id'),
				'text': profile.get('label')
			}).inject(self.mass_edit_quality)
		});

		self.filter_menu.addLink(
			self.navigation_search_input = new Element('input', {
				'title': 'Search through ' + self.options.identifier,
				'placeholder': 'Search through ' + self.options.identifier,
				'events': {
					'keyup': self.search.bind(self),
					'change': self.search.bind(self)
				}
			})
		).addClass('search');

		var available_chars;
		self.filter_menu.addEvent('open', function(){
			self.navigation_search_input.focus();

			// Get available chars and highlight
			if(!available_chars && (self.navigation.isDisplayed() || self.navigation.isVisible()))
				Api.request('media.available_chars', {
					'data': Object.merge({
						'status': self.options.status
					}, self.filter),
					'onSuccess': function(json){
						available_chars = json.chars;

						available_chars.each(function(c){
							self.letters[c.capitalize()].addClass('available')
						})

					}
				});
		});

		self.filter_menu.addLink(
			self.navigation_alpha = new Element('ul.numbers', {
				'events': {
					'click:relay(li.available)': function(e, el){
						self.activateLetter(el.get('data-letter'));
						self.getMovies(true)
					}
				}
			})
		);

		// Actions
		['mass_edit', 'details', 'list'].each(function(view){
			var current = self.current_view == view;
			new Element('li', {
				'class': 'icon2 ' + view + (current ?  ' active ' : ''),
				'data-view': view
			}).inject(self.navigation_actions, current ? 'top' : 'bottom');
		});

		// All
		self.letters['all'] = new Element('li.letter_all.available.active', {
			'text': 'ALL'
		}).inject(self.navigation_alpha);

		// Chars
		chars.split('').each(function(c){
			self.letters[c] = new Element('li', {
				'text': c,
				'class': 'letter_'+c,
				'data-letter': c
			}).inject(self.navigation_alpha);
		});

		// Add menu or hide
		if (self.options.menu.length > 0)
			self.options.menu.each(function(menu_item){
				self.navigation_menu.addLink(menu_item);
			});
		else
			self.navigation_menu.hide();

	},

	calculateSelected: function(){
		var self = this;

		var selected = 0,
			movies = self.movies.length;
		self.movies.each(function(movie){
			selected += movie.isSelected() ? 1 : 0
		});

		var indeterminate = selected > 0 && selected < movies,
			checked = selected == movies && selected > 0;

		self.mass_edit_select.set('indeterminate', indeterminate);

		self.mass_edit_select_class[checked ? 'check' : 'uncheck']();
		self.mass_edit_select_class.element[indeterminate ? 'addClass' : 'removeClass']('indeterminate');

		self.mass_edit_selected.set('text', selected);
	},

	deleteSelected: function(){
		var self = this,
			ids = self.getSelectedMovies(),
			help_msg = self.identifier == 'wanted' ? 'If you do, you won\'t be able to watch them, as they won\'t get downloaded!' : 'Your files will be safe, this will only delete the reference from the CouchPotato manage list';

		var qObj = new Question('Are you sure you want to delete '+ids.length+' movie'+ (ids.length != 1 ? 's' : '') +'?', help_msg, [{
			'text': 'Yes, delete '+(ids.length != 1 ? 'them' : 'it'),
			'class': 'delete',
			'events': {
				'click': function(e){
					(e).preventDefault();
					this.set('text', 'Deleting..');
					Api.request('media.delete', {
						'method': 'post',
						'data': {
							'id': ids.join(','),
							'delete_from': self.options.identifier
						},
						'onSuccess': function(){
							qObj.close();

							var erase_movies = [];
							self.movies.each(function(movie){
								if (movie.isSelected()){
									$(movie).destroy();
									erase_movies.include(movie);
								}
							});

							erase_movies.each(function(movie){
								self.movies.erase(movie);
								movie.destroy();
								self.setCounter(self.counter_count-1);
								self.total_movies--;
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
		var ids = self.getSelectedMovies();

		Api.request('movie.edit', {
			'method': 'post',
			'data': {
				'id': ids.join(','),
				'profile_id': self.mass_edit_quality.get('value')
			},
			'onSuccess': self.search.bind(self)
		});
	},

	refreshSelected: function(){
		var self = this;
		var ids = self.getSelectedMovies();

		Api.request('media.refresh', {
			'method': 'post',
			'data': {
				'id': ids.join(',')
			}
		});
	},

	getSelectedMovies: function(){
		var self = this;

		var ids = [];
		self.movies.each(function(movie){
			if (movie.isSelected())
				ids.include(movie.get('_id'))
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

		self.movies = [];
		if(self.mass_edit_select)
			self.calculateSelected();
		if(self.navigation_alpha)
			self.navigation_alpha.getElements('.active').removeClass('active');

		self.offset = 0;
		if(self.scrollspy){
			//self.load_more.show();
			self.scrollspy.start();
		}
	},

	activateLetter: function(letter){
		var self = this;

		self.reset();

		self.letters[letter || 'all'].addClass('active');
		self.filter.starts_with = letter;

	},

	changeView: function(new_view){
		var self = this;

		self.el
			.removeClass(self.current_view+'_list')
			.addClass(new_view+'_list');

		self.current_view = new_view;
		Cookie.write(self.options.identifier+'_view2', new_view, {duration: 1000});
	},

	getSavedView: function(){
		var self = this;
		return Cookie.read(self.options.identifier+'_view2');
	},

	search: function(){
		var self = this;

		if(self.search_timer) clearTimeout(self.search_timer);
		self.search_timer = (function(){
			var search_value = self.navigation_search_input.get('value');
			if (search_value == self.last_search_value) return;

			self.reset();

			self.activateLetter();
			self.filter.search = search_value;

			self.getMovies(true);

			self.last_search_value = search_value;

		}).delay(250);

	},

	update: function(){
		var self = this;

		self.reset();
		self.getMovies(true);
	},

	getMovies: function(reset){
		var self = this;

		if(self.scrollspy){
			self.scrollspy.stop();
			self.load_more.set('text', 'loading...');
		}

		if(self.movies.length == 0 && self.options.loader){

			self.loader_first = new Element('div.loading').adopt(
				new Element('div.message', {'text': self.options.title ? 'Loading \'' + self.options.title + '\'' : 'Loading...'})
			).inject(self.el, 'top');

			createSpinner(self.loader_first, {
				radius: 4,
				length: 4,
				width: 1
			});

			self.el.setStyle('min-height', 93);

		}

		Api.request(self.options.api_call || 'media.list', {
			'data': Object.merge({
				'type': self.options.type || 'movie',
				'status': self.options.status,
				'limit_offset': self.options.limit ? self.options.limit + ',' + self.offset : null
			}, self.filter),
			'onSuccess': function(json){

				if(reset)
					self.movie_list.empty();

				if(self.loader_first){
					var lf = self.loader_first;
					self.loader_first.addClass('hide');
					self.loader_first = null;
					setTimeout(function(){
						lf.destroy();
					}, 20000);
					self.el.setStyle('min-height', null);
				}

				self.store(json.movies);
				self.addMovies(json.movies, json.total || json.movies.length);
				if(self.scrollspy) {
					self.load_more.set('text', 'load more movies');
					self.scrollspy.start();
				}

				self.checkIfEmpty();
				self.fireEvent('loaded');
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

		var is_empty = self.movies.length == 0 && (self.total_movies == 0 || self.total_movies === undefined);

		if(self.title)
			self.title[is_empty ? 'hide' : 'show']();

		if(self.description)
			self.description.setStyle('display', [is_empty ? 'none' : '']);

		if(is_empty && self.options.on_empty_element){
			self.options.on_empty_element.inject(self.loader_first || self.title || self.movie_list, 'after');

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
