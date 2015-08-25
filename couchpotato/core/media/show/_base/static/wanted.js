var ShowsWanted = new Class({
	Extends: PageBase,

	name: 'wanted',
	title: 'List of TV Shows subscribed to',
	folder_browser: null,
	has_tab: false,

	indexAction: function(){
		var self = this;

		if(!self.wanted){

			// Wanted movies
			self.wanted = new ShowList({
				'identifier': 'wanted',
				'status': 'active',
				'type': 'show',
				'actions': [MA.IMDB, MA.Release, MA.Refresh, MA.Delete],
				'add_new': true,
				'on_empty_element': App.createUserscriptButtons().addClass('empty_wanted')
			});
			$(self.wanted).inject(self.content);
		}

	}

});
