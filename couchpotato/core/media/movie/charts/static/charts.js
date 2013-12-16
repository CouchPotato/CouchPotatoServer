var Charts = new Class({

	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.create();
	},

	create: function(){
		var self = this;

		self.el = new Element('div.charts').grab(
			new Element('h2', {
				'text': 'Charts'
			})
		);

		self.api_request = Api.request('charts.view', {
			'onComplete': self.fill.bind(self)
		});

	},

	fill: function(json){

		var self = this;

		if(!json || json.count == 0){
			self.el.hide();
		}
		else {

			Object.each(json.charts, function(chart){

            var c = new Element('div.chart').grab(
                new Element('h3', {
                    'text': chart.name
                })
            );

            var it = 1;

			Object.each(chart.list, function(movie){

				var m = new Block.Search.MovieItem(movie, {
					'onAdded': function(){
						self.afterAdded(m, movie)
					}
				});
				    m.el.grab( new Element('span.chart_number', { 'text': it++ }));
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
							}))
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
					)

				$(m).inject(c);

			});

			$(c).inject(self.el);

			});

		}

		self.fireEvent('loaded');

	},

	afterAdded: function(m, movie){
		var self = this;

		// Maybe do something here in the future

	},

	toElement: function(){
		return this.el;
	}

})
