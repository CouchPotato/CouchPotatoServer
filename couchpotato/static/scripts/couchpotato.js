var CouchPotato = new Class({

	Implements: [Events, Options],

	defaults: {
		page: 'home',
		action: 'index',
		params: {}
	},

	pages: [],
	block: [],

	initialize: function(){
		var self = this;

		self.global_events = {};
	},

	setup: function(options) {
		var self = this;
		self.setOptions(options);

		self.c = $(document.body);

		self.route = new Route(self.defaults);

		self.createLayout();
		self.createPages();

		if(window.location.hash)
			History.handleInitialState();
		else
			self.openPage(window.location.pathname);

		History.addEvent('change', self.openPage.bind(self));
		self.c.addEvent('click:relay(a[href^=/]:not([target]))', self.pushState.bind(self));
		self.c.addEvent('click:relay(a[href^=http])', self.openDerefered.bind(self));

		// Check if device is touchenabled
		self.touch_device = 'ontouchstart' in window || navigator.msMaxTouchPoints;
		if(self.touch_device)
			self.c.addClass('touch_enabled');

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
		if((!e.meta && Browser.Platform.mac) || (!e.control && !Browser.Platform.mac)){
			(e).preventDefault();
			var url = e.target.get('href');
			if(History.getPath() != url)
				History.push(url);
		}
	},

	isMac: function(){
		return Browser.Platform.mac
	},

	createLayout: function(){
		var self = this;

		self.block.header = new Block();

		self.c.adopt(
			$(self.block.header).addClass('header').adopt(
				new Element('div').adopt(
					self.block.navigation = new Block.Navigation(self, {}),
					self.block.search = new Block.Search(self, {}),
					self.block.more = new Block.Menu(self, {'button_class': 'icon2.cog'})
				)
			),
			self.content = new Element('div.content'),
			self.block.footer = new Block.Footer(self, {})
		);

		var setting_links = [
			new Element('a', {
				'text': 'About CouchPotato',
				'href': App.createUrl('settings/about')
			}),
			new Element('a', {
				'text': 'Check for Updates',
				'events': {
					'click': self.checkForUpdate.bind(self, null)
				}
			}),
			new Element('span.separator'),
			new Element('a', {
				'text': 'Settings',
				'href': App.createUrl('settings/general')
			}),
			new Element('a', {
				'text': 'Logs',
				'href': App.createUrl('log')
			}),
			new Element('span.separator'),
			new Element('a', {
				'text': 'Restart',
				'events': {
					'click': self.restartQA.bind(self)
				}
			}),
			new Element('a', {
				'text': 'Shutdown',
				'events': {
					'click': self.shutdownQA.bind(self)
				}
			})
		];

		setting_links.each(function(a){
			self.block.more.addLink(a)
		});


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
			var pg = new Page[class_name](self, {});
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
			self.current_page.hide();

		try {
			var page = self.pages[page_name] || self.pages.Home;
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

		self.blockPage('You have shutdown. This is what is supposed to happen ;)');
		Api.request('app.shutdown', {
			'onComplete': self.blockPage.bind(self)
		});
		self.checkAvailable(1000);
	},

	shutdownQA: function(){
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

		Updater.check(onComplete);

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
						onAvailable();
					self.unBlockPage();
					self.fireEvent('reload');
				}
			});

		}).delay(delay || 0)
	},

	blockPage: function(message, title){
		var self = this;

		self.unBlockPage();

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
	},

	createUserscriptButtons: function(){

		var host_url = window.location.protocol + '//' + window.location.host;

		return new Element('div.group_userscript').adopt(
			new Element('a.userscript.button', {
				'text': 'Install userscript',
				'href': Api.createUrl('userscript.get')+randomString()+'/couchpotato.user.js',
				'target': '_blank'
			}),
			new Element('span.or[text=or]'),
			new Element('span.bookmarklet').adopt(
				new Element('a.button.orange', {
					'text': '+CouchPotato',
					'href': "javascript:void((function(){var e=document.createElement('script');e.setAttribute('type','text/javascript');e.setAttribute('charset','UTF-8');e.setAttribute('src','" +
							host_url + Api.createUrl('userscript.bookmark') +
							"?host="+ encodeURI(host_url + Api.createUrl('userscript.get')+randomString()+'/') +
					 		"&r='+Math.random()*99999999);document.body.appendChild(e)})());",
					'target': '',
					'events': {
						'click': function(e){
							(e).stop();
							alert('Drag it to your bookmark ;)')
						}
					}
				}),
				new Element('span', {
					'text': '⇽ Drag this to your bookmarks'
				})
			)
		);
	},

	/*
	 * Global events
	 */
	on: function(name, handle){
		var self = this;

		if(!self.global_events[name])
			self.global_events[name] = [];

		self.global_events[name].push(handle);

	},

	trigger: function(name, args, on_complete){
		var self = this;

		if(!self.global_events[name]){ return; }

		if(!on_complete && typeOf(args) == 'function'){
			on_complete = args;
			args = [];
		}

		// Create parallel callback
		var callbacks = [];
		self.global_events[name].each(function(handle, nr){

			callbacks.push(function(callback){
				var results = handle.apply(handle, args || []);
				callback(null, results || null);
			});

		});

		// Fire events
		async.parallel(callbacks, function(err, results){
			if(err) p(err);

			if(on_complete)
				on_complete(results);
		});

	},

	off: function(name, handle){
		var self = this;

		if(!self.global_events[name]) return;

		// Remove single
		if(handle){
			self.global_events[name] = self.global_events[name].erase(handle);
		}
		// Reset full event
		else {
			self.global_events[name] = [];
		}

	}

});
window.App = new CouchPotato();

var Route = new Class({

	defaults: {},
	page: '',
	action: 'index',
	params: {},

	initialize: function(defaults){
		var self = this;
		self.defaults = defaults
	},

	parse: function(){
		var self = this;

		var rep = function (pa) {
			return pa.replace(Api.getOption('url'), '/').replace(App.getOption('base_url'), '/')
		};

		var path = rep(History.getPath());
		if(path == '/' && location.hash){
			path = rep(location.hash.replace('#', '/'))
		}
		self.current = path.replace(/^\/+|\/+$/g, '');
		var url = self.current.split('/');

		self.page = (url.length > 0) ? url.shift() : self.defaults.page;
		self.action = (url.length > 0) ? url.shift() : self.defaults.action;

		self.params = Object.merge({}, self.defaults.params);
		if(url.length > 1){
			var key;
			url.each(function(el, nr){
				if(nr%2 == 0)
					key = el;
				else if(key) {
					self.params[key] = el;
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
			var aVal = valueOf(a, keyPaths[i].path),
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
			return this.stableSort(comparer);
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
};
