var BlockHeader = new Class({

	Extends: BlockNavigation,

	create: function(){
		var self = this;

		self.parent();

		self.el.adopt(
			self.logo = new Element('a.logo', {
				'html': '<span>Couch</span><span>Potato</span>',
				'href': App.createUrl('')
			}),
			self.nav
		);

	}

});
