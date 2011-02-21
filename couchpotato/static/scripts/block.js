var BlockBase = new Class({

	Implements: [Options, Events],

	options: {},

	initialize: function(parent, options){
		var self = this;
		self.setOptions(options);
		
		self.parent = parent;

		self.create();
	},
	
	create: function(){
		this.el = new Element('div.block');
	},

	toElement: function(){
		return this.el
	}

});

var Block = {}