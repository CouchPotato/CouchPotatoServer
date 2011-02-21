var PageBase = new Class({

	Implements: [Options, Events],

	options: {

	},

	has_tab: true,

	initialize: function(parent, options) {
		var self = this;

		self.setOptions(options)
		self.setParent(parent)

		// Create main page container
		self.el = new Element('div.page.'+self.name);

		// Create tab for page
		if(self.has_tab){
			var nav = self.getParent().getBlock('navigation');
			self.tab = nav.addTab({
				'href': '/'+self.name,
				'title': self.title,
				'text': self.name.capitalize()
			});
		}
	},

	open: function(action, params){
		var self = this;
		//p('Opening: ' +self.getName() + ', ' + action + ', ' + Object.toQueryString(params));

		try {
			self[action+'Action'](params);
			self.fireEvent('opened');
		}
		catch (e){
			self.errorAction(e);
			self.fireEvent('error');
		}
	},

	errorAction: function(e){
		p('Error, action not found', e);
	},

	getName: function(){
		return this.name
	},

	setParent: function(parent){
		this.app = parent
	},

	getParent: function(){
		return this.app
	},

	api: function(){
		return this.getParent().getApi()
	},
	
	show: function(){
		this.el.addClass('active');
	},
	
	hide: function(){
		this.el.removeClass('active');
	},
	
	toElement: function(){
		return this.el
	}
});

var Page = {}
