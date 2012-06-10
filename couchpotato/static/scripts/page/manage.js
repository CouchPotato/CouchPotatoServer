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
				'menu': [self.refresh_button, self.refresh_quick]
			});
			$(self.list).inject(self.el);
		}

	},

	refresh: function(full){
		var self = this;

		Api.request('manage.update', {
			'data': {
				'full': +full
			}
		})

	}

});
