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

		self.el = new Element('div.charts').adopt(
			self.el_no_charts_enabled = new Element('p.no_charts_enabled', {
				'html': 'Hey, it looks like you have no charts enabled at the moment. If you\'d like some great movie suggestions you can go to <a href="' + App.createUrl('settings/display') + '">settings</a> and turn on some charts of your choice.'
			}),
			self.el_refresh_container = new Element('div.refresh').adopt(
				self.el_refresh_link = new Element('a.refresh.icon2', {
					'href': '#',
					'events': {
						'click': function(e) {
							e.preventDefault();

							self.el.getElements('.chart').destroy();
							self.el_refreshing_text.show();
							self.el_refresh_link.hide();

							self.api_request = Api.request('charts.view', {
								'data': { 'force_update': 1 },
								'onComplete': self.fill.bind(self)
							});
						}
					}
				}),
				self.el_refreshing_text = new Element('span.refreshing', {
					'text': 'Refreshing charts...'
				})
			)
		);

		self.show();
		self.fireEvent.delay(0, self, 'created');

	},

	fill: function(json){

		var self = this;

		self.el_refreshing_text.hide();
		self.el_refresh_link.show();

		if(!json || json.count === 0){
			self.el_no_charts_enabled.show();
			self.el_refresh_link.show();
			self.el_refreshing_text.hide();
		}
		else {
			self.el_no_charts_enabled.hide();

			json.charts.sort(function(a, b) {
				return a.order - b.order;
			});

			Object.each(json.charts, function(chart){

				var chart_list = new MovieList({
					'navigation': false,
					'identifier': chart.name.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
					'title': chart.name,
					'description': '<a href="'+chart.url+'">See source</a>',
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
			setTimeout(function(){
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
