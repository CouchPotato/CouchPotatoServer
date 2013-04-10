Page.Home = new Class({

	Extends: PageBase,

	name: 'home',
	title: 'Manage new stuff for things and such',

	indexAction: function(param){
		var self = this;

		if(self.soon_list){

			// Reset lists
			self.available_list.update();
			self.late_list.update();

			return
		}

		// Snatched
		self.available_list = new MovieList({
			'navigation': false,
			'identifier': 'snatched',
			'load_more': false,
			'view': 'list',
			'actions': [MA.IMDB, MA.Trailer, MA.Release, MA.Refresh, MA.Delete],
			'title': 'Snatched & Available',
			'on_empty_element': new Element('div'),
			'filter': {
				'release_status': 'snatched,available'
			}
		});

		// Coming Soon
		self.soon_list = new MovieList({
			'navigation': false,
			'identifier': 'soon',
			'limit': 18,
			'title': 'Available soon',
			'description': 'These are being searched for and should be available soon as they will be released on DVD in the next few weeks.',
			'on_empty_element': new Element('div').adopt(
				new Element('h1', {'text': 'Available soon'}),
				new Element('span', {'text': 'There are no movies available soon. Add some movies, so you have something to watch later.'})
			),
			'filter': {
				'random': true
			},
			'actions': [MA.IMDB, MA.Refresh],
			'load_more': false,
			'view': 'thumbs',
			'api_call': 'dashboard.soon'
		});

		// Still not available
		self.late_list = new MovieList({
			'navigation': false,
			'identifier': 'late',
			'limit': 50,
			'title': 'Still not available',
			'description': 'Try another quality profile or maybe add more providers in <a href="'+App.createUrl('settings/searcher/providers/')+'">Settings</a>.',
			'on_empty_element': new Element('div'),
			'filter': {
				'late': true
			},
			'load_more': false,
			'view': 'list',
			'actions': [MA.IMDB, MA.Trailer, MA.Edit, MA.Refresh, MA.Delete],
			'api_call': 'dashboard.soon'
		});

		self.el.adopt(
			$(self.available_list),
			$(self.soon_list),
			$(self.late_list)
		);

		// Suggest
		// self.suggestion_list = new MovieList({
			// 'navigation': false,
			// 'identifier': 'suggestions',
			// 'limit': 6,
			// 'load_more': false,
			// 'view': 'thumbs',
			// 'api_call': 'suggestion.suggest'
		// });
		// self.el.adopt(
			// new Element('h2', {
				// 'text': 'You might like'
			// }),
			// $(self.suggestion_list)
		// );

		// Recent
			// Snatched
			// Renamed
			// Added

		// Free space

		// Shortcuts

	}

})