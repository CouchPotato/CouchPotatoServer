Page.Home = new Class({

	Extends: PageBase,

	name: 'home',
	title: 'Manage new stuff for things and such',

	indexAction: function(param){
		var self = this;

		if(self.soon_list)
			return

		// Snatched
		self.available_list = new MovieList({
			'navigation': false,
			'identifier': 'snatched',
			'load_more': false,
			'view': 'list',
			'actions': MovieActions,
			'title': 'Snatched & Available',
			'filter': {
				'release_status': 'snatched,available'
			}
		});

		// Downloaded
		// self.downloaded_list = new MovieList({
			// 'navigation': false,
			// 'identifier': 'downloaded',
			// 'load_more': false,
			// 'view': 'titles',
			// 'filter': {
				// 'release_status': 'done',
				// 'order': 'release_order'
			// }
		// });
		// self.el.adopt(
			// new Element('h2', {
				// 'text': 'Just downloaded'
			// }),
			// $(self.downloaded_list)
		// );

		// Comming Soon
		self.soon_list = new MovieList({
			'navigation': false,
			'identifier': 'soon',
			'limit': 24,
			'title': 'Soon',
			'filter': {
				'random': true
			},
			'load_more': false,
			'view': 'thumbs',
			'api_call': 'dashboard.soon'
		});

		self.el.adopt(
			$(self.available_list),
			$(self.soon_list)
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