Page.Shows = new Class({

	Extends: PageBase,

	name: 'shows',
	title: 'Gimmy gimmy gimmy!',
	folder_browser: null,

	indexAction: function(){
		var self = this;

		if(!self.wanted){

			// Wanted movies
			self.wanted = new ShowList({
				'identifier': 'wanted',
				'status': 'active',
				'type': 'show',
				'actions': [MA.IMDB, MA.Trailer, MA.Release, MA.Edit, MA.Refresh, MA.Readd, MA.Delete],
				'add_new': true,
				'on_empty_element': App.createUserscriptButtons().addClass('empty_wanted')
			});
			$(self.wanted).inject(self.el);
		}

	}

});
