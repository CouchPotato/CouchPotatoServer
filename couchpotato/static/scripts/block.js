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

	api: function(){
		return this.getParent().getApi()
	},

	getParent: function(){
		return this.page
	},

	toElement: function(){
		return this.el
	}

});

var Block = {}