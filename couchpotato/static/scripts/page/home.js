Page.Home = new Class({

	Extends: PageBase,

	name: 'home',
	title: 'Manage new stuff for things and such',
	icon: 'home',

	indexAction: function () {
		var self = this;

		if(self.soon_list){

			// Reset lists
			self.available_list.update();

			if(self.late_list)
				self.late_list.update();

			return;
		}

		self.chain = new Chain();
		self.chain.chain(
			self.createAvailable.bind(self),
			self.createBigsearch.bind(self),
			self.createSoon.bind(self),
			self.createSuggestions.bind(self),
			self.createCharts.bind(self),
			self.createLate.bind(self)
		);

		self.chain.callChain();

	},

	createBigsearch: function(){
		var self = this;

		new Element('.big_search').grab(
			new BlockSearch(self, {
				'animate': false
			})
		).inject(self.content);

		self.chain.callChain();
	},

	createAvailable: function(){
		var self = this;

		self.available_list = new MovieList({
			'navigation': false,
			'identifier': 'snatched',
			'load_more': false,
			'view': 'list',
			'actions': [MA.MarkAsDone, MA.IMDB, MA.Release, MA.Trailer, MA.Refresh, MA.Readd, MA.Delete, MA.Category, MA.Profile],
			'title': 'Snatched & Available',
			'description': 'These movies have been snatched or have finished downloading',
			'on_empty_element': new Element('div').adopt(
				new Element('h2', {'text': 'Snatched & Available'}),
				new Element('span.no_movies', {
					'html': 'No snatched movies or anything!? Damn.. <a href="#">Maybe add a movie.</a>',
					'events': {
						'click': function(e){
							(e).preventDefault();
							$(document.body).getElement('.big_search input').focus();
						}
					}
				})
			),
			'filter': {
				'release_status': 'snatched,missing,available,downloaded,done,seeding',
				'with_tags': 'recent'
			},
			'limit': null,
			'onLoaded': function(){
				self.chain.callChain();
			},
			'onMovieAdded': function(notification){

				// Track movie added
				var after_search = function(data){
					if(notification.data._id != data.data._id) return;

					// Force update after search
					self.available_list.update();
					App.off('movie.searcher.ended', after_search);
				};
				App.on('movie.searcher.ended', after_search);

			}
		});

		$(self.available_list).inject(self.content);

	},

	createSoon: function(){
		var self = this;

		// Coming Soon
		self.soon_list = new MovieList({
			'navigation': false,
			'identifier': 'soon',
			'limit': 12,
			'title': 'Available soon',
			'description': 'Should be available soon as they will be released on DVD/Blu-ray in the coming weeks.',
			'filter': {
				'random': true
			},
			'actions': [MA.IMDB, MA.Release, MA.Trailer, MA.Refresh, MA.Delete, MA.Category, MA.Profile],
			'load_more': false,
			'view': 'thumb',
			'force_view': true,
			'api_call': 'dashboard.soon',
			'onLoaded': function(){
				self.chain.callChain();
			}
		});

		$(self.soon_list).inject(self.content);

	},

	createSuggestions: function(){
		var self = this;

		self.suggestions_list = new MovieList({
			'navigation': false,
			'identifier': 'suggest',
			'limit': 12,
			'title': 'Suggestions',
			'description': 'Based on your current wanted and managed items',
			'actions': [MA.Add, MA.SuggestIgnore, MA.SuggestSeen, MA.IMDB, MA.Trailer],
			'load_more': false,
			'view': 'thumb',
			'force_view': true,
			'api_call': 'suggestion.view',
			'onLoaded': function(){
				self.chain.callChain();
			}
		});

		$(self.suggestions_list).inject(self.content);

	},

	createCharts: function(){
		var self = this;

		// Charts
		self.charts_list = new Charts({
			'onCreated': function(){
				self.chain.callChain();
			}
		});

		$(self.charts_list).inject(self.content);

	},

	createLate: function(){
		var self = this;

		// Still not available
		self.late_list = new MovieList({
			'navigation': false,
			'identifier': 'late',
			'limit': 50,
			'title': 'Still not available',
			'description': 'Try another quality profile or maybe add more providers in <a href="' + App.createUrl('settings/searcher/providers/') + '">Settings</a>.',
			'filter': {
				'late': true
			},
			'loader': false,
			'load_more': false,
			'view': 'list',
			'actions': [MA.IMDB, MA.Trailer, MA.Refresh, MA.Delete, MA.Category, MA.Profile],
			'api_call': 'dashboard.soon',
			'onLoaded': function(){
				self.chain.callChain();
			}
		});

		$(self.late_list).inject(self.content);

	}

});
