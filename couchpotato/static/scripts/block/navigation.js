var BlockNavigation = new Class({

	Extends: BlockBase,

	create: function(){
		var self = this;

		self.el = new Element('div.navigation').grab(
			self.nav = new Element('ul')
		);

	},

	addTab: function(name, tab){
		var self = this;

		return new Element('li.tab_'+(name || 'unknown')).grab(
			new Element('a', tab)
		).inject(self.nav);

	},

	activate: function(name){
		var self = this;

		self.nav.getElements('.active').removeClass('active');
		self.nav.getElements('.tab_'+name).addClass('active');

	}

});
