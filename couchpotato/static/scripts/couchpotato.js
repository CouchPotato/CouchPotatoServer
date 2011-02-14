var CouchPotato = new Class({

	Implements: [Options],

	defaults: {
		page: 'movie',
		action: 'index',
		params: {}
	},

	pages: [],
	
	tabse: [
	    {'href': 'movie', 'title':'Gimmy gimmy gimmy!', 'label':'Wanted'},
	    {'href': 'manage', 'title':'Do stuff to your existing movies!', 'label':'Manage'},
	    {'href': 'feed', 'title':'Which wanted movies are released soon?', 'label':'Soon'},
	    {'href': 'log', 'title':'Show recent logs.', 'class':'logLink', 'label':'Logs'},
	    {'href': 'config', 'title':'Change settings.', 'id':'showConfig'}
	],

	initialize: function(options) {
		var self = this;
		self.setOptions(options);
		
		self.c = $(document.body)

		self.route = new Route();

		History.addEvent('change', self.createPage.bind(self));
		History.handleInitialState();
		
		self.createLayout()
	},
	
	createLayout: function(){
		var self = this;
		
		self.c.adopt(
			self.header = new Element('div.header').adopt(
				self.navigation = new Element('ul.navigation'),
				self.add_form = new Element('div.add_form')
			),
			self.content = new Element('div.content'),
			self.footer = new Element('div.footer')
		)
	},

	createPage: function(url) {
		var self = this;

		self.route.parse(url);
		var page = self.route.getPage().capitalize();
		var action = self.route.getAction();
		var params = self.route.getParams();

		if(!self.pages[page]){
			page = new Page[page]();
			self.pages[page] = page;
		}
		page = self.pages[page]
		page.open(action, params)

	}
});

var PageBase = new Class({

	Implements: [Options],

	initialize: function(options) {

	},

	open: function(action, params){
		var self = this;
		console.log(action, params, self.getName());

	},

	getName: function(){
		return this.name
	}
});

var Route = new Class({

	page: '',
	action: 'index',
	params: {},

	parse: function(url){
		var self = this;

		url = url.split('/')
		self.page = url.shift()
		self.action = url.shift()
		self.params = {}

		var key
		url.each(function(el, nr){
			if(nr%2 == 0)
				key = el
			else if(key) {
				self.params[key] = el
				key = null
			}
		})

		return self
	},

	getPage: function(){
		return this.page
	},

	getAction: function(){
		return this.action
	},

	getParams: function(){
		return this.params
	},

	get: function(param){
		return this.params[param]
	}

});