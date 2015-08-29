var BlockSearch = new Class({

	Extends: BlockBase,

	options: {
		'animate': true
	},

	cache: {},

	create: function(){
		var self = this;

		var focus_timer = 0;
		self.el = new Element('div.search_form').adopt(
			new Element('a.icon-search', {
				'events': {
					'click': self.clear.bind(self)
				}
			}),
			self.wrapper = new Element('div.wrapper').adopt(
				self.result_container = new Element('div.results_container', {
					'events': {
						'mousewheel': function(e){
							(e).stopPropagation();
						}
					}
				}).grab(
					self.results = new Element('div.results')
				),
				new Element('div.input').grab(
					self.input = new Element('input', {
						'placeholder': 'Search & add a new media',
						'events': {
							'input': self.keyup.bind(self),
							'paste': self.keyup.bind(self),
							'change': self.keyup.bind(self),
							'keyup': self.keyup.bind(self),
							'focus': function(){
								if(focus_timer) clearRequestTimeout(focus_timer);
								if(this.get('value'))
									self.hideResults(false);
							},
							'blur': function(){
								focus_timer = requestTimeout(function(){
									self.el.removeClass('focused');
									self.last_q = null;
								}, 100);
							}
						}
					})
				)
			)
		);

		self.mask = new Element('div.mask').inject(self.result_container);

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
			self.el.addClass('focused');
			self.input.focus();

			self.media = {};
			self.results.empty();
			self.el.removeClass('filled');

			// Animate in
			if(self.options.animate){

				dynamics.css(self.wrapper, {
					opacity: 0,
					scale: 0.1
				});

				dynamics.animate(self.wrapper, {
					opacity: 1,
					scale: 1
				}, {
					type: dynamics.spring,
					frequency: 200,
					friction: 270,
					duration: 800
				});

			}

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

			if(self.autocomplete_timer) clearRequestTimeout(self.autocomplete_timer);
			self.autocomplete_timer = requestTimeout(self.autocomplete.bind(self), 300);
		}

	},

	autocomplete: function(){
		var self = this;

		if(!self.q()){
			self.hideResults(true);
			return;
		}

		self.list();
	},

	list: function(){
		var self = this,
			q = self.q(),
			cache = self.cache[q];

		self.hideResults(false);

		if(!cache){
			requestTimeout(function(){
				self.mask.addClass('show');
			}, 10);

			if(!self.spinner)
				self.spinner = createSpinner(self.mask);

			self.api_request = Api.request('search', {
				'data': {
					'q': q
				},
				'onComplete': self.fill.bind(self, q)
			});
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
				Object.each(media, function(me){

					var m = new window['BlockSearch' + me.type.capitalize() + 'Item'](me);
					$(m).inject(self.results);
					self.media[m.imdb || 'r-'+Math.floor(Math.random()*10000)] = m;

					if(q == m.imdb)
						m.showOptions();

				});
			}
		});

		self.mask.removeClass('show');

	},

	loading: function(bool){
		this.el[bool ? 'addClass' : 'removeClass']('loading');
	},

	q: function(){
		return this.input.get('value').trim();
	}

});
