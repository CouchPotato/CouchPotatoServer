Page.Shows = new Class({

	Extends: PageBase,

	name: 'shows',
	title: 'List of TV Shows subscribed to',
	folder_browser: null,
	has_tab: false,

	toggleShows: function(arg) {
		var self = this;
		var nav = App.getBlock('navigation');

		if ((typeof arg === 'object' && arg.data === true) || arg === true) {
			self.tab = nav.addTab(self.name, {
				'href': App.createUrl(self.name),
				'title': self.title,
				'text': self.name.capitalize()
			});
			self.has_tab = true;
		} else {
			self.has_tab = false;
			self.tab = null;
			nav.removeTab('shows');
		}
	},

	load: function() {
		var self = this;

		Api.request('settings', {
			'onComplete': function(json){
				self.toggleShows(json.values.shows.enabled);
			}
		});

		App.on('shows.enabled', self.toggleShows.bind(self));
	},

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
