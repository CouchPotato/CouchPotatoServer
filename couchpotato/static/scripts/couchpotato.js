var CouchPotato = new Class({

	Implements: [Options],

	defaults: {
		page: 'wanted',
		action: 'index',
		params: {}
	},

	pages: [],
	block: [],

	initialize: function(options) {
		var self = this;
		self.setOptions(options);

		self.c = $(document.body)

		self.route = new Route(self.defaults);
		self.api = new Api(self.options.api)

		self.createLayout();
		self.createPages();

		History.addEvent('change', self.openPage.bind(self));
		History.handleInitialState();

		self.c.addEvent('click:relay(a)', self.pushState.bind(self));
	},

	pushState: function(e){
		var self = this;
		(e).stop();

		var url = e.target.get('href');
		if(History.getPath() != url)
			History.push(url);
	},

	createLayout: function(){
		var self = this;

		self.c.adopt(
			self.header = new Element('div.header').adopt(
				self.block.navigation = new Block.Navigation(self, {}),
				self.block.search = new Block.Search(self, {})
			),
			self.content = new Element('div.content'),
			self.block.footer = new Block.Footer(self, {})
		);
	},

	createPages: function(){
		var self = this;

		Object.each(Page, function(page_class, class_name){
			pg = new Page[class_name](self, {});
			self.pages[class_name] = pg;

			$(pg).inject(self.content);
		});

	},

	openPage: function(url) {
		var self = this;

		self.route.parse(url);
		var page_name = self.route.getPage().capitalize();
		var action = self.route.getAction();
		var params = self.route.getParams();

		var page = self.pages[page_name];
			page.open(action, params);
			page.show();

		if(self.current_page)
			self.current_page.hide()

		self.current_page = page;

	},

	getBlock: function(block_name){
		return this.block[block_name]
	},

	getApi: function(){
		return this.api
	}
});


var Api = new Class({

	url: '',

	initialize: function(options){
		var self = this

		self.options = options;
		self.req = new Request.JSON({
			'method': 'get'
		})

	},

	request: function(type, options){
		var self = this;

		return new Request.JSON(Object.merge({
			'method': 'get',
			'url': self.createUrl(type),
		}, options)).send()
	},

	createUrl: function(action){
		return this.options.url + (action || 'default') + '/'
	},

	getOption: function(name){
		return this.options[name]
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