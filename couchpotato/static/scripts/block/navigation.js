Block.Navigation = new Class({

	Extends: BlockBase,

	create: function(){
		var self = this;

		self.el = new Element('ul.navigation');
	},

	addTab: function(tab){
		var self = this

		return new Element('li').adopt(
			new Element('a', tab)
		).inject(self.el)

	}

});