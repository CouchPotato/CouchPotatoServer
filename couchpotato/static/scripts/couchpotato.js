var CouchPotato = new Class({

	Implements: [Options],

	defaults: {
		page: 'movie',
		action: 'index',
		params: {}
	},

	pages: [],

	tabs: [
	    {'href': '/movie/', 'title':'Gimmy gimmy gimmy!', 'label':'Wanted'},
	    {'href': '/manage/', 'title':'Do stuff to your existing movies!', 'label':'Manage'},
	    {'href': '/feed/', 'title':'Which wanted movies are released soon?', 'label':'Soon'},
	    {'href': '/log/', 'title':'Show recent logs.', 'class':'logLink', 'label':'Logs'},
	    {'href': '/config/', 'title':'Change settings.', 'id':'showConfig'}
	],

	initialize: function(options) {
		var self = this;
		self.setOptions(options);

		self.c = $(document.body)

		self.route = new Route(self.defaults);
		self.api = new Api(self.options.api_url)

		History.addEvent('change', self.createPage.bind(self));
		History.handleInitialState();

		self.createLayout()
		self.createNavigation()

		self.c.addEvent('click:relay(a)', self.openPage.bind(self))
	},

	openPage: function(e){
		var self = this;
		(e).stop()

		var url = e.target.get('href')
		History.push(url)
	},

	createNavigation: function(){
		var self = this

		self.tabs.each(function(tab){
			new Element('li').adopt(
				new Element('a', {
					'href': tab.href,
					'title': tab.title,
					'text': tab.label
				})
			).inject(self.navigation)
		})

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
		var page_name = self.route.getPage().capitalize();
		var action = self.route.getAction();
		var params = self.route.getParams();

		var pg = self.pages[page_name]
		if(!pg){
			pg = new Page[page_name]();
			pg.setParent(self)
			self.pages[page_name] = pg;
		}
		pg.open(action, params)

	},

	getApi: function(){
		return this.api
	}
});

var PageBase = new Class({

	Implements: [Options],

	initialize: function(options) {

	},

	open: function(action, params){
		var self = this;
		p('Opening: ' +self.getName() + ', ' + action + ', ' + Object.toQueryString(params));

		try {
			self[action+'Action'](params)
		}
		catch (e){
			self.errorAction(e)
		}
	},

	errorAction: function(e){
		p('Error, action not found', e);
	},

	getName: function(){
		return this.name
	},

	setParent: function(parent){
		this.parent = parent
	},

	getParent: function(){
		return this.parent
	},

	api: function(){
		return this.parent.getApi()
	}
});

var Api = new Class({

	url: '',

	initialize: function(url){
		var self = this

		self.url = url
		self.req = new Request.JSON({
			'method': 'get'
		})

	},

	request: function(type, params, data){
		var self = this;

		self.req.setOptions({
			'url': self.createUrl(type, params),
			'data': data
		})
		self.req.send()
	},

	createUrl: function(action, params){
		return this.url + (action || 'default') + '/?' + Object.toQueryString(params)
	}

});

var Route = new Class({

	defaults: {},
	page: '',
	action: 'index',
	params: {},

	initialize: function(defaults){
		var self = this
		self.defaults = defaults
	},

	parse: function(url_string){
		var self = this;

		var current = History.getPath().replace(/^\/+|\/+$/g, '')
		var url = current.split('/')

		self.page = (url.length > 0) ? url.shift() : self.defaults.page
		self.action = (url.length > 0) ? url.shift() : self.defaults.action

		self.params = self.defaults.params
		if(url.length > 1){
			var key
			url.each(function(el, nr){
				if(nr%2 == 0)
					key = el
				else if(key) {
					self.params[key] = el
					key = null
				}
			})
		}

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

var p = function(){
	if(typeof(console) !== 'undefined' && console != null)
		console.log(arguments)
}