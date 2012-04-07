var BlockBase = new Class({

	Implements: [Options, Events],

	options: {},

	initialize: function(parent, options){
		var self = this;
		self.setOptions(options);

		self.page = parent;

		self.create();

	},

	create: function(){
		this.el = new Element('div.block');
	},

	getParent: function(){
		return this.page
	},

	hide: function(){
		this.el.hide();
	},

	show: function(){
		this.el.show();
	},

	toElement: function(){
		return this.el
	}

});

var Block = BlockBase