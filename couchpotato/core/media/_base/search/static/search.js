Block.Search = new Class({

	Extends: BlockBase,

	cache: {},

	create: function(){
		var self = this;

		var focus_timer = 0;
		self.el = new Element('div.search_form').adopt(
			new Element('div.input').adopt(
				self.input = new Element('input', {
					'placeholder': 'Search & add a new media',
					'events': {
						'input': self.keyup.bind(self),
						'paste': self.keyup.bind(self),
						'change': self.keyup.bind(self),
						'keyup': self.keyup.bind(self),
						'focus': function(){
							if(focus_timer) clearTimeout(focus_timer);
							self.el.addClass('focused');
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
			self.input.blur();
			self.last_q = null;
		}
		else {

			self.last_q = '';
			self.input.set('value', '');
			self.input.focus();

			self.media = {};
			self.results.empty();
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

	keyup: function(){
		var self = this;

		self.el[self.q() ? 'addClass' : 'removeClass']('filled');

		if(self.q() != self.last_q){
			if(self.api_request && self.api_request.isRunning())
				self.api_request.cancel();

			if(self.autocomplete_timer) clearTimeout(self.autocomplete_timer);
			self.autocomplete_timer = self.autocomplete.delay(300, self)
		}

	},

	autocomplete: function(){
		var self = this;

		if(!self.q()){
			self.hideResults(true);
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

			self.api_request = Api.request('search', {
				'data': {
					'q': q
				},
				'onComplete': self.fill.bind(self, q)
			})
		}
		else
			self.fill(q, cache);

		self.last_q = q;

	},

	fill: function(q, json){
		var self = this;

		self.cache[q] = json;

		self.media = {};
		self.results.empty();

		Object.each(json, function(media){
			if(typeOf(media) == 'array'){
				Object.each(media, function(m){

					var m = new Block.Search[m.type.capitalize() + 'Item'](m);
					$(m).inject(self.results);
					self.media[m.imdb || 'r-'+Math.floor(Math.random()*10000)] = m;

					if(q == m.imdb)
						m.showOptions()

				});
			}
		});

		// Calculate result heights
		var w = window.getSize(),
			rc = self.result_container.getCoordinates();

		self.results.setStyle('max-height', (w.y - rc.top - 50) + 'px');
		self.mask.fade('out')

	},

	loading: function(bool){
		this.el[bool ? 'addClass' : 'removeClass']('loading')
	},

	q: function(){
		return this.input.get('value').trim();
	}

});
