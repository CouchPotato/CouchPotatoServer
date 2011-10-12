var CouchPotato = new Class({

	Implements: [Events, Options],

	defaults: {
		page: 'wanted',
		action: 'index',
		params: {}
	},

	pages: [],
	block: [],

	setup: function(options) {
		var self = this;
		self.setOptions(options);

		self.c = $(document.body)

		self.route = new Route(self.defaults);

		self.createLayout();
		self.createPages();

		History.addEvent('change', self.openPage.bind(self));

		if(window.location.hash)
			History.handleInitialState();
		else
			self.openPage(window.location.pathname);

		self.c.addEvent('click:relay(a:not([target=_blank]))', self.pushState.bind(self));
	},

	getOption: function(name){
		return this.options[name];
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

		self.block.header = new Block();

		self.c.adopt(
			$(self.block.header).addClass('header').adopt(
				new Element('div').adopt(
					self.block.navigation = new Block.Navigation(self, {}),
					self.block.search = new Block.Search(self, {})
				)
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

		self.load_timer = (function(){
			self.fireEvent('load');
		}).delay(1000);

	},
	
	stopLoadTimer: function(){
		if(this.load_timer)
			clearInterval(this.load_timer);
	},

	openPage: function(url) {
		var self = this;

		self.route.parse(url);
		var page_name = self.route.getPage().capitalize();
		var action = self.route.getAction();
		var params = self.route.getParams();

		if(self.current_page)
			self.current_page.hide()

		try {
			var page = self.pages[page_name] || self.pages.Wanted;
				page.open(action, params);
				page.show();
		}
		catch(e){
			p("Can't open page:" + url)
		}

		self.current_page = page;

	},

	getBlock: function(block_name){
		return this.block[block_name]
	},

	getPage: function(name){
		return this.pages[name]
	},

	shutdown: function(){
		Api.request('app.shutdown');
	},

	restart: function(){
		Api.request('app.restart');
	}

});
window.App = new CouchPotato();

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

		var path = History.getPath().replace(Api.getOption('url'), '/') //Remove API front
		var current = path.replace(/^\/+|\/+$/g, '')
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
};


(function(){
	var events;

	var check = function(e) {
		var target = $(e.target);
		var parents = target.getParents();
		events.each(function(item) {
			var element = item.element;
			if (element != target && !parents.contains(element))
				item.fn.call(element, e);
		});
	};

	Element.Events.outerClick = {
		onAdd : function(fn) {
			if (!events) {
				document.addEvent('click', check);
				events = [];
			}
			events.push( {
				element : this,
				fn : fn
			});
		},

		onRemove : function(fn) {
			events = events.filter(function(item) {
				return item.element != this || item.fn != fn;
			}, this);
			if (!events.length) {
				document.removeEvent('click', check);
				events = null;
			}
		}
	};
})();


function randomString(length, extra) {
	var chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz" + (extra ? '-._!@#$%^&*()+=' : '');
	var stringLength = length || 8;
	var randomString = '';
	for (var i = 0; i < stringLength; i++) {
		var rnum = Math.floor(Math.random() * chars.length);
		randomString += chars.charAt(rnum);
	}
	return randomString;
}

(function(){

	var keyPaths = [];

	var saveKeyPath = function(path) {
		keyPaths.push({
			sign: (path[0] === '+' || path[0] === '-')? parseInt(path.shift()+1) : 1,
			path: path
		});
	};

	var valueOf = function(object, path) {
		var ptr = object;
		path.each(function(key) { ptr = ptr[key] });
		return ptr;
	};

	var comparer = function(a, b) {
		for (var i = 0, l = keyPaths.length; i < l; i++) {
			aVal = valueOf(a, keyPaths[i].path);
			bVal = valueOf(b, keyPaths[i].path);
			if (aVal > bVal) return keyPaths[i].sign;
			if (aVal < bVal) return -keyPaths[i].sign;
		}
		return 0;
	};

	Array.implement('sortBy', function(){
		keyPaths.empty();
		Array.each(arguments, function(argument) {
			switch (typeOf(argument)) {
				case "array": saveKeyPath(argument); break;
				case "string": saveKeyPath(argument.match(/[+-]|[^.]+/g)); break;
			}
		});
		return this.sort(comparer);
	});

})();