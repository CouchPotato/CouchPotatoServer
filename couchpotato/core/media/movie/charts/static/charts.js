var Charts = new Class({

	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.create();
	},

	create: function(){
		var self = this;

		self.el = new Element('div.charts');


		self.el_toggle_menu = new Element('div.toggle_menu', {

        });

        self.el_toggle_menu.grab( new Element('a.toggle_suggestions.active', {
                'href': '#',
                'events': { 'click': function(e) {
                        e.preventDefault();
                        self.toggle_menu('suggestions');
                    }
                }
            }).grab( new Element('h2', {'text': 'Suggestions'}))
		);
		self.el_toggle_menu.grab( new Element('a.toggle_charts', {
                'href': '#',
                'events': { 'click': function(e) {
                        e.preventDefault();
                        self.toggle_menu('charts');
                    }
                }
            }).grab( new Element('h2', {'text': 'Charts'}))
		);


		self.api_request = Api.request('charts.view', {
			'onComplete': self.fill.bind(self)
		});

	},

	toggle_menu: function(menu_id){
	    var self = this;
	    var menu_list = ['suggestions','charts'];
	    var menu_index = -1;
	    for( var i = 0; i < menu_list.length; i++) {
	        if( menu_id == menu_list[i] ) {
	            menu_index = i;
	            break;
	        }
	    }
	    if( menu_index == -1 ) return false;

	    for( var i = 0; i < menu_list.length; i++) {
	        if( i != menu_index ) {
	            $$('div.'+menu_list[i]).hide();
	            $$('a.toggle_'+menu_list[i]).removeClass('active');
	        };
	    }

	    $$('div.'+menu_id).show();
	    $$('a.toggle_'+menu_id).addClass('active');
	    return true;
	},

	fill: function(json){

		var self = this;

		if(!json || json.count == 0){
			self.el.hide();
		}
		else {
            self.el_toggle_menu.inject( self.el, 'before');

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
				    var in_database_class = movie.in_wanted ? '.chart_in_wanted' : (movie.in_library ? '.chart_in_library' : '');
				    var in_database_title = movie.in_wanted ? 'Movie in wanted list' : (movie.in_library ? 'Movie in library' : '');
				    m.el.grab( new Element('div.chart_number' + in_database_class, { 'text': it++, 'title': in_database_title }));
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

		$(m).getElement('div.chart_number').addClass('chart_in_wanted').setProperty('title','Movie in wanted list');


	},

	toElement: function(){
		return this.el;
	}

})
