Page.Wanted = new Class({

	Extends: PageBase,

	name: 'wanted',
	title: 'Gimmy gimmy gimmy!',

	indexAction: function(param){
		var self = this;

		if(!self.wanted){

			self.manual_search = new Element('a', {
				'title': 'Force a search for the full wanted list',
				'text': 'Search all wanted',
				'events':{
					'click': self.doFullSearch.bind(self, true)
				}
			});

			// Wanted movies
			self.wanted = new MovieList({
				'identifier': 'wanted',
				'status': 'active',
				'actions': [MA.IMDB, MA.Trailer, MA.Release, MA.Edit, MA.Refresh, MA.Readd, MA.Delete],
				'add_new': true,
				'menu': [self.manual_search],
				'on_empty_element': App.createUserscriptButtons().addClass('empty_wanted')
			});
			$(self.wanted).inject(self.el);

			// Check if search is in progress
			self.startProgressInterval.delay(4000, self);
		}

	},

	doFullSearch: function(full){
		var self = this;

		if(!self.search_in_progress){

			Api.request('searcher.full_search');
			self.startProgressInterval();

		}

	},

	startProgressInterval: function(){
		var self = this;

		var start_text = self.manual_search.get('text');
		self.progress_interval = setInterval(function(){
			if(self.search_progress && self.search_progress.running) return;
			self.search_progress = Api.request('searcher.progress', {
				'onComplete': function(json){
					self.search_in_progress = true;
					if(!json.progress){
						clearInterval(self.progress_interval);
						self.search_in_progress = false;
						self.manual_search.set('text', start_text);
					}
					else {
						var progress = json.progress;
						self.manual_search.set('text', 'Searching.. (' + (((progress.total-progress.to_go)/progress.total)*100).round() + '%)');
					}
				}
			});
		}, 1000);

	}

});