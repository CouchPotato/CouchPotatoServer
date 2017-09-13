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

		self.createLayout();
		self.createPages();

		if(window.location.hash)
			History.handleInitialState();
		else
			self.openPage(window.location.pathname);

		History.addEvent('change', self.openPage.bind(self));
		self.c.addEvent('click:relay(.header a, .navigation a, .movie_details a, .list_list .movie)', self.ripple.bind(self));
		self.c.addEvent('click:relay(a[href^=/]:not([target]))', self.pushState.bind(self));
		self.c.addEvent('click:relay(a[href^=http])', self.openDerefered.bind(self));

		// Check if device is touchenabled
		self.touch_device = 'ontouchstart' in window || navigator.msMaxTouchPoints;
		if(self.touch_device){
			self.c.addClass('touch_enabled');
			FastClick.attach(document.body);
		}

		window.addEvent('resize', self.resize.bind(self));
		self.resize();

		//self.checkCache();

	},

	checkCache: function(){
		window.addEventListener('load', function() {
			window.applicationCache.addEventListener('updateready', function(e) {
				if (window.applicationCache.status == window.applicationCache.UPDATEREADY) {
					window.applicationCache.swapCache();
					window.location.reload();
				}
			}, false);

		}, false);
	},

	resize: function(){
		var self = this;

		self.mobile_screen = Math.max(document.documentElement.clientWidth, window.innerWidth || 0) <= 480;
		self.c[self.mobile_screen ? 'addClass' : 'removeClass']('mobile');
	},

	ripple: function(e, el){
		var self = this,
			button = el.getCoordinates(),
			x = e.page.x - button.left,
			y = e.page.y - button.top,
			ripple = new Element('div.ripple', {
				'styles': {
					'left': x,
					'top': y
				}
			});

		ripple.inject(el);

		requestTimeout(function(){ ripple.addClass('animate'); }, 0);
		requestTimeout(function(){ ripple.dispose(); }, 2100);
	},

	getOption: function(name){
		try {
			return this.options[name];
		}
		catch(e){
			return null;
		}
	},

	pushState: function(e, el){
		var self = this;

		if((!e.meta && App.isMac()) || (!e.control && !App.isMac())){
			(e).preventDefault();
			var url = el.get('href');

			// Middle click
			if(e.event && e.event.button === 1)
				window.open(url);
			else if(History.getPath() != url)
				History.push(url);

		}

		self.fireEvent('history.push');
	},

	isMac: function(){
		return Browser.platform == 'mac';
	},

	createLayout: function(){
		var self = this;

		// TODO : sorry, it's a crutch... Need to move self.hide_update initialization to appropriate place..
		// WebUI Feature:
		self.hide_update = !! App.options && App.options.webui_feature && App.options.webui_feature.hide_menuitem_update;

		self.block.header = new BlockBase();

		self.c.adopt(
			$(self.block.header).addClass('header').adopt(
				self.block.navigation = new BlockHeader(self, {}),
				self.block.search = new BlockSearch(self, {}),
				self.support = new Element('a.donate.icon-donate', {
					'href': 'https://couchpota.to/support/',
					'target': '_blank'
				}).grab(
					new Element('span', {
						'text': 'Donate'
					})
				),
				self.block.more = new BlockMenu(self, {'button_class': 'icon-settings'})
			),
			new Element('div.corner_background'),
			self.content = new Element('div.content').adopt(
				self.pages_container = new Element('div.pages'),
				self.block.footer = new BlockFooter(self, {})
			)
		);

		var setting_links = [
			new Element('a', {
				'text': 'About CouchPotato',
				'href': App.createUrl('settings/about')
			}),
			new Element('a', {
				'text': 'Settings',
				'href': App.createUrl('settings/general')
			}),
			new Element('a', {
				'text': 'Logs',
				'href': App.createUrl('log')
			}),
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

		if (!self.hide_update){
			setting_links.splice(1, 0, new Element('a', {
				'text': 'Check for Updates',
				'events': {
					'click': self.checkForUpdate.bind(self, null)
				}
			}));
		}

		setting_links.each(function(a){
			self.block.more.addLink(a);
		});

		// Set theme
		self.addEvent('setting.save.core.dark_theme', function(enabled){
			document.html[enabled ? 'addClass' : 'removeClass']('dark');
		});

	},

	createPages: function(){
		var self = this;

		var pages = [];
		Object.each(Page, function(page_class, class_name){
			var pg = new Page[class_name](self, {
				'level': 1
			});
			self.pages[class_name] = pg;

			pages.include({
				'order': pg.order,
				'name': class_name,
				'class': pg
			});
		});

		pages.stableSort(self.sortPageByOrder).each(function(page){
			page['class'].load();
			self.fireEvent('load'+page.name);
			$(page['class']).inject(self.getPageContainer());
		});

		self.fireEvent('load');

	},

	sortPageByOrder: function(a, b){
		return (a.order || 100) - (b.order || 100);
	},

	openPage: function(url) {
		var self = this,
			route = new Route(self.defaults);

		route.parse(rep(History.getPath()));

		var page_name = route.getPage().capitalize(),
			action = route.getAction(),
			params = route.getParams(),
			current_url = route.getCurrentUrl(),
			page;

		if(current_url == self.current_url)
			return;

		if(self.current_page)
			self.current_page.hide();

		try {
			page = self.pages[page_name] || self.pages.Home;
			page.open(action, params, current_url);
			page.show();
		}
		catch(e){
			console.error("Can't open page:" + url, e);
		}

		self.current_page = page;
		self.current_url = current_url;

	},

	getBlock: function(block_name){
		return this.block[block_name];
	},

	getPage: function(name){
		return this.pages[name];
	},

	getPageContainer: function(){
		return this.pages_container;
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
					requestTimeout(q.close.bind(q), 100);
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
					requestTimeout(q.close.bind(q), 100);
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

		requestTimeout(function(){

			var onFailure = function(){
				requestTimeout(function(){
					self.checkAvailable(delay, onAvailable);
				}, 1000);
				self.fireEvent('unload');
			};

			var request = Api.request('app.available', {
				'timeout': 2000,
				'onTimeout': function(){
					request.cancel();
					onFailure();
				},
				'onFailure': onFailure,
				'onSuccess': function(){
					if(onAvailable)
						onAvailable();
					self.unBlockPage();
					self.fireEvent('reload');
				}
			});

		}, delay || 0);
	},

	blockPage: function(message, title){
		var self = this;

		self.unBlockPage();

		self.mask = new Element('div.mask.with_message').adopt(
			new Element('div.message').adopt(
				new Element('h1', {'text': title || 'Unavailable'}),
				new Element('div', {'text': message || 'Something must have crashed.. check the logs ;)'})
			)
		).inject(document.body);

		createSpinner(self.mask);

		requestTimeout(function(){
			self.mask.addClass('show');
		}, 10);
	},

	unBlockPage: function(){
		var self = this;
		if(self.mask)
			self.mask.get('tween').start('opacity', 0).chain(function(){
				this.element.destroy();
			});
	},

	createUrl: function(action, params){
		return this.options.base_url + (action ? action+'/' : '') + (params ? '?'+Object.toQueryString(params) : '');
	},

	openDerefered: function(e, el){
		var self = this;
		(e).stop();

		var url = el.get('href');
		if(self.getOption('dereferer')){
			url = self.getOption('dereferer') + el.get('href');
		}

		if(el.get('target') == '_blank' || (e.meta && self.isMac()) || (e.control && !self.isMac()))
			window.open(url);
		else
			window.location = url;
	},

	createUserscriptButtons: function(){

		var host_url = window.location.protocol + '//' + window.location.host;

		return new Element('div.group_userscript').adopt(
			new Element('div').adopt(
				new Element('a.userscript.button', {
					'text': 'Install extension',
					'href': 'https://couchpota.to/extension/',
					'target': '_blank'
				}),
				new Element('span.or[text=or]'),
				new Element('span.bookmarklet').adopt(
					new Element('a.button', {
						'text': '+CouchPotato',
						/* jshint ignore:start */
						'href': "javascript:void((function(){var e=document.createElement('script');e.setAttribute('type','text/javascript');e.setAttribute('charset','UTF-8');e.setAttribute('src','" +
						host_url + Api.createUrl('userscript.bookmark') +
						"?host="+ encodeURI(host_url + Api.createUrl('userscript.get')+randomString()+'/') +
						"&r='+Math.random()*99999999);document.body.appendChild(e)})());",
						/* jshint ignore:end */
						'target': '',
						'events': {
							'click': function(e){
								(e).stop();
								alert('Drag it to your bookmark ;)');
							}
						}
					}),
					new Element('span', {
						'text': '⇽ Drag this to your bookmarks'
					})
				)
			),
			new Element('img', {
				'src': 'https://couchpota.to/media/images/userscript.gif'
			})
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
		self.global_events[name].each(function(handle){

			requestTimeout(function(){
				var results = handle.apply(handle, args || []);

				if(on_complete)
					on_complete(results);
			}, 0);
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

	defaults: null,
	page: '',
	action: 'index',
	params: {},

	initialize: function(defaults){
		var self = this;
		self.defaults = defaults || {};
	},

	parse: function(path){
		var self = this;

		if(path == '/' && location.hash){
			path = rep(location.hash.replace('#', '/'));
		}
		self.current = path.replace(/^\/+|\/+$/g, '');
		var url = self.current.split('/');

		self.page = (url.length > 0) ? url.shift() : self.defaults.page;
		self.action = (url.length > 0) ? url.join('/') : self.defaults.action;

		self.params = Object.merge({}, self.defaults.params);
		if(url.length > 1){
			var key;
			url.each(function(el, nr){
				if(nr%2 === 0)
					key = el;
				else if(key) {
					self.params[key] = el;
					key = null;
				}
			});
		}
		else if(url.length == 1){
			self.params[url] = true;
		}

		return self;
	},

	getPage: function(){
		return this.page;
	},

	getAction: function(){
		return this.action;
	},

	getParams: function(){
		return this.params;
	},

	getCurrentUrl: function(){
		return this.current;
	},

	get: function(param){
		return this.params[param];
	}

});

var p = function(){
	if(typeof(console) !== 'undefined' && console !== null)
		console.log(arguments);
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
	var chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz" + (extra ? '-._!@#$%^&*()+=' : ''),
		string_length = length || 8,
		random_string = '';
	for (var i = 0; i < string_length; i++) {
		var rnum = Math.floor(Math.random() * chars.length);
		random_string += chars.charAt(rnum);
	}
	return random_string;
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
		path.each(function(key) { ptr = ptr[key]; });
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

var createSpinner = function(container){
	var spinner = new Element('div.spinner');
	container.grab(spinner);
	return spinner;
};

var rep = function (pa) {
	return pa.replace(Api.getOption('url'), '/').replace(App.getOption('base_url'), '/');
};
