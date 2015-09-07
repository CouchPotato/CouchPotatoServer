var MoviesWanted = new Class({

	Extends: PageBase,

	order: 10,
	name: 'wanted',
	title: 'Gimme gimme gimme!',
	folder_browser: null,

	indexAction: function(){
		var self = this;

		if(!self.list){

			self.manual_search = new Element('a', {
				'title': 'Force a search for the full wanted list',
				'text': 'Search all wanted',
				'events':{
					'click': self.doFullSearch.bind(self, true)
				}
			});

			self.scan_folder = new Element('a', {
				'title': 'Scan a folder and rename all movies in it',
				'text': 'Manual folder scan',
				'events':{
					'click': self.scanFolder.bind(self)
				}
			});

			// Wanted movies
			self.list = new MovieList({
				'identifier': 'wanted',
				'status': 'active',
				'actions': [MA.MarkAsDone, MA.IMDB, MA.Release, MA.Trailer, MA.Refresh, MA.Readd, MA.Delete, MA.Category, MA.Profile],
				'add_new': true,
				'menu': [self.manual_search, self.scan_folder],
				'on_empty_element': function(){
					return new Element('div.empty_wanted').adopt(
						new Element('div.no_movies', {
							'text': 'Seems like you don\'t have any movies yet.. Maybe add some via search or the extension.'
						}),
						App.createUserscriptButtons()
					);
				}
			});
			$(self.list).inject(self.content);

			// Check if search is in progress
			requestTimeout(self.startProgressInterval.bind(self), 4000);
		}

	},

	doFullSearch: function(){
		var self = this;

		if(!self.search_in_progress){

			Api.request('movie.searcher.full_search');
			self.startProgressInterval();

		}

	},

	startProgressInterval: function(){
		var self = this;

		var start_text = self.manual_search.get('text');
		self.progress_interval = requestInterval(function(){
			if(self.search_progress && self.search_progress.running) return;
			self.search_progress = Api.request('movie.searcher.progress', {
				'onComplete': function(json){
					self.search_in_progress = true;
					if(!json.movie){
						clearRequestInterval(self.progress_interval);
						self.search_in_progress = false;
						self.manual_search.set('text', start_text);
					}
					else {
						var progress = json.movie;
						self.manual_search.set('text', 'Searching.. (' + Math.round(((progress.total-progress.to_go)/progress.total)*100) + '%)');
					}
				}
			});
		}, 1000);

	},

	scanFolder: function(e) {
		(e).stop();

		var self = this;
		var options = {
			'name': 'Scan_folder'
		};

		if(!self.folder_browser){
			self.folder_browser = new Option.Directory("Scan", "folder", "", options);

			self.folder_browser.save = function() {
				var folder = self.folder_browser.getValue();
				Api.request('renamer.scan', {
					'data': {
						'base_folder': folder
					}
				});
			};

			self.folder_browser.inject(self.content, 'top');
			self.folder_browser.fireEvent('injected');

			// Hide the settings box
			self.folder_browser.directory_inlay.hide();
			self.folder_browser.el.removeChild(self.folder_browser.el.firstChild);

			self.folder_browser.showBrowser();

			// Make adjustments to the browser
			self.folder_browser.browser.getElements('.clear.button').hide();
			self.folder_browser.save_button.text = "Select";
			self.folder_browser.browser.setStyles({
				'z-index': 1000,
				'right': 20,
				'top': 0,
				'margin': 0
			});

			self.folder_browser.pointer.setStyles({
				'right': 20
			});

		}
		else{
			self.folder_browser.showBrowser();
		}

		self.list.navigation_menu.hide();
	}

});
