Page.Manage = new Class({

	Extends: PageBase,

	order: 20,
	name: 'manage',
	title: 'Do stuff to your existing movies!',

	indexAction: function(){
		var self = this;

		if(!self.list){
			self.refresh_button = new Element('a', {
				'title': 'Rescan your library for new movies',
				'text': 'Full library refresh',
				'events':{
					'click': self.refresh.bind(self, true)
				}
			});

			self.refresh_quick = new Element('a', {
				'title': 'Just scan for recently changed',
				'text': 'Quick library scan',
				'events':{
					'click': self.refresh.bind(self, false)
				}
			});

			self.list = new MovieList({
				'identifier': 'manage',
				'filter': {
					'status': 'done',
					'release_status': 'done',
					'status_or': 1
				},
				'actions': [MA.IMDB, MA.Trailer, MA.Files, MA.Readd, MA.Edit, MA.Delete],
				'menu': [self.refresh_button, self.refresh_quick],
				'on_empty_element': new Element('div.empty_manage').adopt(
					new Element('div', {
						'text': 'Seems like you don\'t have anything in your library yet.'
					}),
					new Element('div', {
						'text': 'Add your existing movie folders in '
					}).adopt(
						new Element('a', {
							'text': 'Settings > Manage',
							'href': App.createUrl('settings/manage')
						})
					),
					new Element('div.after_manage', {
						'text': 'When you\'ve done that, hit this button → '
					}).adopt(
						new Element('a.button.green', {
							'text': 'Hit me, but not too hard',
							'events':{
								'click': self.refresh.bind(self, true)
							}
						})
					)
				)
			});
			$(self.list).inject(self.el);

			// Check if search is in progress
			self.startProgressInterval();
		}

	},

	refresh: function(full){
		var self = this;

		if(!self.update_in_progress){

			Api.request('manage.update', {
				'data': {
					'full': +full
				}
			});

			self.startProgressInterval();

		}

	},

	startProgressInterval: function(){
		var self = this;

		self.progress_interval = setInterval(function(){

			if(self.progress_request && self.progress_request.running)
				return;

			self.update_in_progress = true;
			self.progress_request = Api.request('manage.progress', {
				'onComplete': function(json){

					if(!json || !json.progress){
						clearInterval(self.progress_interval);
						self.update_in_progress = false;
						if(self.progress_container){
							self.progress_container.destroy();
							self.list.update();
						}
					}
					else {
						// Capture progress so we can use it in our *each* closure
						var progress = json.progress;

						// Don't add loader when page is loading still
						if(!self.list.navigation)
							return;

						if(!self.progress_container)
							self.progress_container = new Element('div.progress').inject(self.list.navigation, 'after');

						self.progress_container.empty();

						var sorted_table = self.parseProgress(json.progress);

						sorted_table.each(function(folder){
							var folder_progress = progress[folder];
							new Element('div').adopt(
								new Element('span.folder', {'text': folder +
									(folder_progress.eta > 0 ? ', ' + new Date ().increment('second', folder_progress.eta).timeDiffInWords().replace('from now', 'to go') : '')
								}),
								new Element('span.percentage', {'text': folder_progress.total ? Math.round(((folder_progress.total-folder_progress.to_go)/folder_progress.total)*100) + '%' : '0%'})
							).inject(self.progress_container)
						});

					}
				}
			})

		}, 1000);
	},

	parseProgress: function (progress_object) {
		var folder, temp_array = [];

		for (folder in progress_object) {
			if (progress_object.hasOwnProperty(folder)) {
				temp_array.push(folder)
			}
		}
		return temp_array.stableSort()
	}

});
