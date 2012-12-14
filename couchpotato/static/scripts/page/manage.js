Page.Manage = new Class({

	Extends: PageBase,

	name: 'manage',
	title: 'Do stuff to your existing movies!',

	indexAction: function(param){
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
				'status': 'done',
				'actions': MovieActions,
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
			})

			self.startProgressInterval();

		}

	},

	startProgressInterval: function(){
		var self = this;

		self.progress_interval = setInterval(function(){

			Api.request('manage.progress', {
				'onComplete': function(json){
					self.update_in_progress = true;

					if(!json.progress){
						clearInterval(self.progress_interval);
						self.update_in_progress = false;
						if(self.progress_container){
							self.progress_container.destroy();
							self.list.update();
						}
					}
					else {
						if(!self.progress_container)
							self.progress_container = new Element('div.progress').inject(self.list.navigation, 'after')

						self.progress_container.empty();

						Object.each(json.progress, function(progress, folder){
							new Element('div').adopt(
								new Element('span.folder', {'text': folder}),
								new Element('span.percentage', {'text': progress.total ? (((progress.total-progress.to_go)/progress.total)*100).round() + '%' : '0%'})
							).inject(self.progress_container)
						});

					}
				}
			})

		}, 1000);

	}

});
