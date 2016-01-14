var Charts = new Class({

	Implements: [Options, Events],

	shown_once: false,

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		self.create();
	},

	create: function(){
		var self = this;

		self.el = new Element('div.charts').grab(
			self.el_refresh_container = new Element('div.refresh').grab(
				self.el_refreshing_text = new Element('span.refreshing', {
					'text': 'Refreshing charts...'
				})
			)
		);

		self.show();

		requestTimeout(function(){
			self.fireEvent('created');
		}, 0);
	},

	fill: function(json){

		var self = this;

		self.el_refreshing_text.hide();

		if(json && json.count > 0){
			json.charts.sort(function(a, b) {
				return a.order - b.order;
			});

			Object.each(json.charts, function(chart){

				var chart_list = new MovieList({
					'navigation': false,
					'identifier': chart.name.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
					'title': chart.name,
					'description': '<a href="'+chart.url+'" target="_blank">See source</a>',
					'actions': [MA.Add, MA.ChartIgnore, MA.IMDB, MA.Trailer],
					'load_more': false,
					'view': 'thumb',
					'force_view': true,
					'api_call': null
				});

				// Load movies in manually
				chart_list.store(chart.list);
				chart_list.addMovies(chart.list, chart.list.length);
				chart_list.checkIfEmpty();
				chart_list.fireEvent('loaded');

				$(chart_list).inject(self.el);

			});

		}

		self.fireEvent('loaded');

	},

	show: function(){
		var self = this;

		self.el.show();

		if(!self.shown_once){
			requestTimeout(function(){
				self.api_request = Api.request('charts.view', {
					'onComplete': self.fill.bind(self)
				});
			}, 100);

			self.shown_once = true;
		}
	},

	toElement: function(){
		return this.el;
	}

});
