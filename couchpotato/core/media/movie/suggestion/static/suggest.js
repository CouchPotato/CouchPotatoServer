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

					$(el).getParent('.media_result').destroy();

					Api.request('suggestion.ignore', {
						'data': {
							'imdb': el.get('data-ignore')
						},
						'onComplete': self.fill.bind(self)
					});

				},
				'click:relay(a.eye-open)': function(e, el){
					(e).stop();

					$(el).getParent('.media_result').destroy();

					Api.request('suggestion.ignore', {
						'data': {
							'imdb': el.get('data-seen'),
							'mark_seen': 1
						},
						'onComplete': self.fill.bind(self)
					});

				}
			}
		});

        var cookie_menu_select = Cookie.read('suggestions_charts_menu_selected');
        if( cookie_menu_select === 'suggestions' || cookie_menu_select === null ) self.el.show(); else self.el.hide();

		self.api_request = Api.request('suggestion.view', {
			'onComplete': self.fill.bind(self)
		});

	},

	fill: function(json){

		var self = this;

		if(!json || json.count == 0){
			self.el.hide();
		}
		else {

			Object.each(json.suggestions, function(movie){

				var m = new Block.Search.MovieItem(movie, {
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
							}),
							new Element('a.eye-open.icon2', {
								'title': 'Seen it, like it, don\'t add',
								'data-seen': movie.imdb
							})
						)
					);
					m.data_container.removeEvents('click');

					var plot = false;
					if(m.info.plot && m.info.plot.length > 0)
						plot = m.info.plot;

					// Add rating
					m.info_container.adopt(
						m.rating = m.info.rating && m.info.rating.imdb && m.info.rating.imdb.length == 2 && parseFloat(m.info.rating.imdb[0]) > 0  ? new Element('span.rating', {
							'text': parseFloat(m.info.rating.imdb[0]),
							'title': parseInt(m.info.rating.imdb[1]) + ' votes'
						}) : null,
						m.genre = m.info.genres && m.info.genres.length > 0 ? new Element('span.genres', {
							'text': m.info.genres.slice(0, 3).join(', ')
						}) : null,
						m.plot = plot ? new Element('span.plot', {
							'text': plot,
							'events': {
								'click': function(){
									this.toggleClass('full')
								}
							}
						}) : null
					);

				$(m).inject(self.el);

			});

		}

		self.fireEvent('loaded');

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

});
