Block.Search = new Class({

	Extends: BlockBase,

	cache: {},

	create: function(){
		var self = this;

		self.el = new Element('div.search_form').adopt(
			self.input = new Element('input', {
				'events': {
					'keyup': self.keyup.bind(self)
				}
			}),
			self.results = new Element('div.results')
		);

		// Debug
		self.input.set('value', 'iron man');
		self.autocomplete(0)
	},

	keyup: function(e){
		var self = this;

		if(['up', 'down'].indexOf(e.key) > -1){
			p('select item')
		}
		else if(self.q() != self.last_q) {
			self.autocomplete()
		}

	},

	autocomplete: function(delay){
		var self = this;

		if(self.autocomplete_timer) clearTimeout(self.autocomplete_timer)
		self.autocomplete_timer = self.list.delay((delay || 300), self)
	},

	list: function(){
		var self = this;

		if(self.api_request) self.api_request.cancel();

		var q = self.q();
		var cache = self.cache[q];

		if(!cache)
			self.api_request = self.api().request('movie.add.search', {
				'data': {
					'q': q
				},
				'onComplete': self.fill.bind(self, q)
			})
		else
			self.fill(q, cache)

		self.last_q = q;

	},

	fill: function(q, json){
		var self = this;

		self.cache[q] = json

		self.movies = []
		self.results.empty()

		Object.each(json.movies, function(movie){
			var m = new Block.Search.Item(movie);
			$(m).inject(self.results)

			self.movies.include(m)
		});

	},

	q: function(){
		return this.input.get('value').trim();
	}

});

Block.Search.Item = new Class({

	initialize: function(info){
		var self = this;

		self.info = info;

		self.create();
	},

	create: function(){
		var self = this;

		self.el = new Element('div.movie').adopt(
			self.name = new Element('h2', {
				'text': self.info.name
			}),
			self.tagline = new Element('span', {
				'text': self.info.tagline
			}),
			self.year = self.info.year ? new Element('span', {
				'text': self.info.year
			}) : null,
			self.director = self.info.director ?  new Element('span', {
				'text': 'Director:' + self.info.director
			}) : null,
			self.starring = self.info.actors ? new Element('span', {
				'text': 'Starring:'
			}) : null
		)
		
		if(self.info.actors){
			Object.each(self.info.actors, function(actor){
				new Element('span', {
					'text': actor.name
				}).inject(self.starring)
			})
		}
	},

	toElement: function(){
		return this.el
	}

})
