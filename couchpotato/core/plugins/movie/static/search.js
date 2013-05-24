Block.Search = new Class({

	Extends: BlockBase,

	cache: {},

	create: function(){
		var self = this;

		var focus_timer = 0;
		self.el = new Element('div.search_form').adopt(
			new Element('div.input').adopt(
				self.input = new Element('input', {
					'placeholder': 'Search & add a new movie',
					'events': {
						'keyup': self.keyup.bind(self),
						'focus': function(){
							if(focus_timer) clearTimeout(focus_timer);
							self.el.addClass('focused')
							if(this.get('value'))
								self.hideResults(false)
						},
						'blur': function(){
							focus_timer = (function(){
								self.el.removeClass('focused')
							}).delay(100);
						}
					}
				}),
				new Element('a.icon2', {
					'events': {
						'click': self.clear.bind(self),
						'touchend': self.clear.bind(self)
					}
				})
			),
			self.result_container = new Element('div.results_container', {
				'tween': {
					'duration': 200
				},
				'events': {
					'mousewheel': function(e){
						(e).stopPropagation();
					}
				}
			}).adopt(
				self.results = new Element('div.results')
			)
		);

		self.mask = new Element('div.mask').inject(self.result_container).fade('hide');

	},

	clear: function(e){
		var self = this;
		(e).preventDefault();

		if(self.last_q === ''){
			self.input.blur()
			self.last_q = null;
		}
		else {

			self.last_q = '';
			self.input.set('value', '');
			self.input.focus()

			self.movies = []
			self.results.empty()
			self.el.removeClass('filled')

		}
	},

	hideResults: function(bool){
		var self = this;

		if(self.hidden == bool) return;

		self.el[bool ? 'removeClass' : 'addClass']('shown');

		if(bool){
			History.removeEvent('change', self.hideResults.bind(self, !bool));
			self.el.removeEvent('outerClick', self.hideResults.bind(self, !bool));
		}
		else {
			History.addEvent('change', self.hideResults.bind(self, !bool));
			self.el.addEvent('outerClick', self.hideResults.bind(self, !bool));
		}

		self.hidden = bool;
	},

	keyup: function(e){
		var self = this;

		self.el[self.q() ? 'addClass' : 'removeClass']('filled')

		if(self.q() != self.last_q){
			if(self.api_request && self.api_request.isRunning())
				self.api_request.cancel();

			if(self.autocomplete_timer) clearTimeout(self.autocomplete_timer)
			self.autocomplete_timer = self.autocomplete.delay(300, self)
		}

	},

	autocomplete: function(){
		var self = this;

		if(!self.q()){
			self.hideResults(true)
			return
		}

		self.list()
	},

	list: function(){
		var self = this,
			q = self.q(),
			cache = self.cache[q];

		self.hideResults(false);

		if(!cache){
			self.mask.fade('in');

			if(!self.spinner)
				self.spinner = createSpinner(self.mask);

			self.api_request = Api.request('movie.search', {
				'data': {
					'q': q
				},
				'onComplete': self.fill.bind(self, q)
			})
		}
		else
			self.fill(q, cache)

		self.last_q = q;

	},

	fill: function(q, json){
		var self = this;

		self.cache[q] = json

		self.movies = {}
		self.results.empty()

		Object.each(json.movies, function(movie){

			var m = new Block.Search.Item(movie);
			$(m).inject(self.results)
			self.movies[movie.imdb || 'r-'+Math.floor(Math.random()*10000)] = m

			if(q == movie.imdb)
				m.showOptions()

		});

		// Calculate result heights
		var w = window.getSize(),
			rc = self.result_container.getCoordinates();

		self.results.setStyle('max-height', (w.y - rc.top - 50) + 'px')
		self.mask.fade('out')

	},

	loading: function(bool){
		this.el[bool ? 'addClass' : 'removeClass']('loading')
	},

	q: function(){
		return this.input.get('value').trim();
	}

});

Block.Search.Item = new Class({

	initialize: function(info, options){
		var self = this;

		self.info = info;
		self.alternative_titles = [];

		self.create();
	},

	create: function(){
		var self = this,
			info = self.info;

		self.el = new Element('div.movie_result', {
			'id': info.imdb
		}).adopt(
			self.thumbnail = info.images && info.images.poster.length > 0 ? new Element('img.thumbnail', {
				'src': info.images.poster[0],
				'height': null,
				'width': null
			}) : null,
			self.options_el = new Element('div.options.inlay'),
			self.data_container = new Element('div.data', {
				'tween': {
					duration: 400,
					transition: 'quint:in:out'
				},
				'events': {
					'click': self.showOptions.bind(self)
				}
			}).adopt(
				new Element('div.info').adopt(
					self.title = new Element('h2', {
						'text': info.titles[0]
					}).adopt(
						self.year = info.year ? new Element('span.year', {
							'text': info.year
						}) : null
					)
				)
			)
		)


		info.titles.each(function(title){
			self.alternativeTitle({
				'title': title
			});
		})
	},

	alternativeTitle: function(alternative){
		var self = this;

		self.alternative_titles.include(alternative);
	},

	showOptions: function(){
		var self = this;

		self.createOptions();

		self.data_container.addClass('open');
		self.el.addEvent('outerClick', self.closeOptions.bind(self))

	},

	closeOptions: function(){
		var self = this;

		self.data_container.removeClass('open');
		self.el.removeEvents('outerClick')
	},

	add: function(e){
		var self = this;
		(e).preventDefault();

		self.loadingMask();

		Api.request('movie.add', {
			'data': {
				'identifier': self.info.imdb,
				'title': self.title_select.get('value'),
				'profile_id': self.profile_select.get('value')
			},
			'onComplete': function(json){
				self.options_el.empty();
				self.options_el.adopt(
					new Element('div.message', {
						'text': json.added ? 'Movie successfully added.' : 'Movie didn\'t add properly. Check logs'
					})
				);
				self.mask.fade('out');
			},
			'onFailure': function(){
				self.options_el.empty();
				self.options_el.adopt(
					new Element('div.message', {
						'text': 'Something went wrong, check the logs for more info.'
					})
				);
				self.mask.fade('out');
			}
		});
	},

	createOptions: function(){
		var self = this,
			info = self.info;

		if(!self.options_el.hasClass('set')){

			if(self.info.in_library){
				var in_library = [];
				self.info.in_library.releases.each(function(release){
					in_library.include(release.quality.label)
				});
			}

			self.options_el.grab(
				new Element('div', {
					'class': self.info.in_wanted && self.info.in_wanted.profile || in_library ? 'in_library_wanted' : ''
				}).adopt(
					self.info.in_wanted && self.info.in_wanted.profile ? new Element('span.in_wanted', {
						'text': 'Already in wanted list: ' + self.info.in_wanted.profile.label
					}) : (in_library ? new Element('span.in_library', {
						'text': 'Already in library: ' + in_library.join(', ')
					}) : null),
					self.title_select = new Element('select', {
						'name': 'title'
					}),
					self.profile_select = new Element('select', {
						'name': 'profile'
					}),
					new Element('a.button', {
						'text': 'Add',
						'events': {
							'click': self.add.bind(self)
						}
					})
				)
			);

			Array.each(self.alternative_titles, function(alt){
				new Element('option', {
					'text': alt.title
				}).inject(self.title_select)
			})

			Quality.getActiveProfiles().each(function(profile){
				new Element('option', {
					'value': profile.id ? profile.id : profile.data.id,
					'text': profile.label ? profile.label : profile.data.label
				}).inject(self.profile_select)
			});

			self.options_el.addClass('set');
		}

	},

	loadingMask: function(){
		var self = this;

		self.mask = new Element('div.mask').inject(self.el).fade('hide')

		createSpinner(self.mask)
		self.mask.fade('in')

	},

	toElement: function(){
		return this.el
	}

});
