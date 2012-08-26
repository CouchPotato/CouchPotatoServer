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

		if(window.location.hash)
			History.handleInitialState();

		self.openPage(window.location.pathname);

		History.addEvent('change', self.openPage.bind(self));
		self.c.addEvent('click:relay(a[href^=/]:not([target]))', self.pushState.bind(self));
		self.c.addEvent('click:relay(a[href^=http])', self.openDerefered.bind(self));
	},

	getOption: function(name){
		try {
			return this.options[name];
		}
		catch(e){
			return null
		}
	},

	pushState: function(e){
		var self = this;
		if((!e.meta && Browser.Platform.mac) || (!e.control && !Browser.Platform.mac)){
			(e).preventDefault();
			var url = e.target.get('href');
			if(History.getPath() != url)
				History.push(url);
		}
	},

	createLayout: function(){
		var self = this;

		self.block.header = new Block();

		self.c.adopt(
			$(self.block.header).addClass('header').adopt(
				new Element('div').adopt(
					self.block.navigation = new Block.Navigation(self, {}),
					self.block.search = new Block.Search(self, {}),
					self.block.more = new Block.Menu(self, {})
				)
			),
			self.content = new Element('div.content'),
			self.block.footer = new Block.Footer(self, {})
		);

		[new Element('a.orange', {
			'text': 'Restart',
			'events': {
				'click': self.restartQA.bind(self)
			}
		}),
		new Element('a.red', {
			'text': 'Shutdown',
			'events': {
				'click': self.shutdownQA.bind(self)
			}
		}),
		new Element('a', {
			'text': 'Update to latest',
			'events': {
				'click': self.checkForUpdate.bind(self, null)
			}
		}),
		new Element('a', {
			'text': 'Run install wizard',
			'href': App.createUrl('wizard')
		})].each(function(a){
			self.block.more.addLink(a)
		})


		new ScrollSpy({
			min: 10,
			onLeave: function(){
				$(self.block.header).removeClass('with_shadow')
			},
			onEnter: function(){
				$(self.block.header).addClass('with_shadow')
			}
		})
	},

	createPages: function(){
		var self = this;

		Object.each(Page, function(page_class, class_name){
			pg = new Page[class_name](self, {});
			self.pages[class_name] = pg;

			$(pg).inject(self.content);
		});

		self.fireEvent('load');

	},

	openPage: function(url) {
		var self = this;

		self.route.parse();
		var page_name = self.route.getPage().capitalize();
		var action = self.route.getAction();
		var params = self.route.getParams();

		var current_url = self.route.getCurrentUrl();
		if(current_url == self.current_url)
			return;

		if(self.current_page)
			self.current_page.hide()

		try {
			var page = self.pages[page_name] || self.pages.Wanted;
			page.open(action, params, current_url);
			page.show();
		}
		catch(e){
			console.error("Can't open page:" + url, e)
		}

		self.current_page = page;
		self.current_url = current_url;

	},

	getBlock: function(block_name){
		return this.block[block_name]
	},

	getPage: function(name){
		return this.pages[name]
	},

	shutdown: function(){
		var self = this;

		self.blockPage('You have shutdown. This is what suppose to happen ;)');
		Api.request('app.shutdown', {
			'onComplete': self.blockPage.bind(self)
		});
		self.checkAvailable(1000);
	},

	shutdownQA: function(e){
		var self = this;

		var q = new Question('Are you sure you want to shutdown CouchPotato?', '', [{
			'text': 'Shutdown',
			'class': 'shutdown red',
			'events': {
				'click': function(e){
					(e).preventDefault();
					self.shutdown();
					q.close.delay(100, q);
				}
			}
		}, {
			'text': 'No, nevah!',
			'cancel': true
		}]);
	},

	restart: function(message, title){
		var self = this;

		self.blockPage(message || 'Restarting... please wait. If this takes too long, something must have gone wrong.', title);
		Api.request('app.restart');
		self.checkAvailable(1000);
	},

	restartQA: function(e, message, title){
		var self = this;

		var q = new Question('Are you sure you want to restart CouchPotato?', '', [{
			'text': 'Restart',
			'class': 'restart orange',
			'events': {
				'click': function(e){
					(e).preventDefault();
					self.restart(message, title);
					q.close.delay(100, q);
				}
			}
		}, {
			'text': 'No, nevah!',
			'cancel': true
		}]);
	},

	checkForUpdate: function(onComplete){
		var self = this;

		Updater.check(onComplete)

		self.blockPage('Please wait. If this takes too long, something must have gone wrong.', 'Checking for updates');
		self.checkAvailable(3000);
	},

	checkAvailable: function(delay, onAvailable){
		var self = this;

		(function(){

			Api.request('app.available', {
				'onFailure': function(){
					self.checkAvailable.delay(1000, self, [delay, onAvailable]);
					self.fireEvent('unload');
				},
				'onSuccess': function(){
					if(onAvailable)
						onAvailable()
					self.unBlockPage();
					self.fireEvent('reload');
				}
			});

		}).delay(delay || 0)
	},

	blockPage: function(message, title){
		var self = this;

		self.unBlockPage();

		var body = $(document.body);
		self.mask = new Element('div.mask').adopt(
			new Element('div').adopt(
				new Element('h1', {'text': title || 'Unavailable'}),
				new Element('div', {'text': message || 'Something must have crashed.. check the logs ;)'})
			)
		).fade('hide').inject(document.body).fade('in');

		createSpinner(self.mask, {
			'top': -50
		});
	},

	unBlockPage: function(){
		var self = this;
		if(self.mask)
			self.mask.get('tween').start('opacity', 0).chain(function(){
				this.element.destroy()
			});
	},

	createUrl: function(action, params){
		return this.options.base_url + (action ? action+'/' : '') + (params ? '?'+Object.toQueryString(params) : '')
	},

	openDerefered: function(e, el){
		(e).stop();

		var url = 'http://www.dereferer.org/?' + el.get('href');

		if(el.get('target') == '_blank' || (e.meta && Browser.Platform.mac) || (e.control && !Browser.Platform.mac))
			window.open(url);
		else
			window.location = url;
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

	parse: function(){
		var self = this;

		var path = History.getPath().replace(Api.getOption('url'), '/').replace(App.getOption('base_url'), '/')
		self.current = path.replace(/^\/+|\/+$/g, '')
		var url = self.current.split('/')

		self.page = (url.length > 0) ? url.shift() : self.defaults.page
		self.action = (url.length > 0) ? url.shift() : self.defaults.action

		self.params = Object.merge({}, self.defaults.params);
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
		else if(url.length == 1){
			self.params[url] = true;
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

	getCurrentUrl: function(){
		return this.current
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

	Array.implement({
		sortBy: function(){
			keyPaths.empty();

			Array.each(arguments, function(argument) {
				switch (typeOf(argument)) {
					case "array": saveKeyPath(argument); break;
					case "string": saveKeyPath(argument.match(/[+-]|[^.]+/g)); break;
				}
			});
			return this.sort(comparer);
		}
	});

})();

var createSpinner = function(target, options){
	var opts = Object.merge({
		lines: 12,
		length: 5,
		width: 4,
		radius: 9,
		color: '#fff',
		speed: 1.9,
		trail: 53,
		shadow: false,
		hwaccel: true,
		className: 'spinner',
		zIndex: 2e9,
		top: 'auto',
		left: 'auto'
	}, options);

	return new Spinner(opts).spin(target);
}