Page.Manage = new Class({

	Extends: PageBase,

	name: 'manage',
	title: 'Do stuff to your existing movies!',

	indexAction: function(param){
		var self = this;

		if(!self.list){
			self.refresh_button = new Element('a.icon.refresh', {
				'text': 'Refresh',
				'events':{
					'click': self.refresh.bind(self)
				}
			}).inject(self.el);

			self.list = new MovieList({
				'identifier': 'manage',
				'status': 'done',
				'actions': MovieActions
			});
			$(self.list).inject(self.el);
		}

	},

	refresh: function(){
		var self = this;

		Api.request('manage.update')

	}

});
