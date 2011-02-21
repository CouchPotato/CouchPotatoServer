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
		});
	},

	get: function(status, onComplete){
		var self = this

		if(self.movies.length == 0)
			self.api().request('movie', {
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

		self.parent(self, options);
	},

	create: function(){
		var self = this;

		self.el = new Element('div.movie', {
			'text': self.data.name
		});

	}

})
