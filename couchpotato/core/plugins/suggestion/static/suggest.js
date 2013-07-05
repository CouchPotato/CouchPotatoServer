var SuggestList = new Class({

	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.create();
	},

	create: function(){
		var self = this;

		self.el = new Element('div.suggestions', {
			'events': {
				'click:relay(a.delete)': function(e, el){
					(e).stop();

					$(el).getParent('.movie_result').destroy();

					Api.request('suggestion.ignore', {
						'data': {
							'imdb': el.get('data-ignore')
						},
						'onComplete': self.fill.bind(self)
					});

				}
			}
		}).grab(
			new Element('h2', {
				'text': 'You might like these'
			})
		);

		self.api_request = Api.request('suggestion.view', {
			'onComplete': self.fill.bind(self)
		});

	},

	fill: function(json){

		var self = this;

		Object.each(json.suggestions, function(movie){

			var m = new Block.Search.Item(movie, {
				'onAdded': function(){
					self.afterAdded(m, movie)
				}
			});
				m.data_container.grab(
					new Element('div.actions').adopt(
						new Element('a.add.icon2', {
							'title': 'Add movie with your default quality',
							'data-add': movie.imdb,
							'events': {
								'click': m.showOptions.bind(m)
							}
						}),
						$(new MA.IMDB(m)),
						$(new MA.Trailer(m, {
							'height': 150
						})),
						new Element('a.delete.icon2', {
							'title': 'Don\'t suggest this movie again',
							'data-ignore': movie.imdb
						})
					)
				);
				m.data_container.removeEvents('click');
			$(m).inject(self.el);

		});

	},

	afterAdded: function(m, movie){
		var self = this;

		setTimeout(function(){
			$(m).destroy();

			Api.request('suggestion.ignore', {
				'data': {
					'imdb': movie.imdb,
					'remove_only': true
				},
				'onComplete': self.fill.bind(self)
			});

		}, 3000);

	},

	toElement: function(){
		return this.el;
	}

})
