Page.Queue = new Class({

	Extends: PageBase,

	name: 'queue',
	title: 'Movies waiting!',

	indexAction: function(param){
		var self = this;

		if(!self.list){
			self.refresh_button = new Element('a', {
				'title': 'List by add date',
				'text': 'Order by date',
				'events':{
					'click': self.refresh.bind(self, true)
				}
			});

			self.refresh_quick = new Element('a', {
				'title': 'List by alphabetic order',
				'text': 'Order by alphabetic',
				'events':{
					'click': self.refresh.bind(self, false)
				}
			});

			self.list = new MovieList({
				'identifier': 'manage',
				'status': 'snatched',
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
