Page.Manage = new Class({

	Extends: PageBase,

	name: 'manage',
	title: 'Do stuff to your existing movies!',

	indexAction: function(param){
		var self = this;

		self.list = new MovieList({
			'status': 'done',
			'actions': Manage.Action
		});
		$(self.list).inject(self.el);
		
	}

});

var Manage = {
	'Action': {
		'IMBD': IMDBAction
	}
}

