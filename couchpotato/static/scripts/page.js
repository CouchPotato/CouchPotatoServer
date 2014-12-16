var PageBase = new Class({

	Implements: [Options, Events],

	options: {

	},

	order: 1,
	has_tab: true,
	name: '',

	parent_page: null,
	sub_pages: null,

	initialize: function(parent_page, options) {
		var self = this;

		self.parent_page = parent_page;
		self.setOptions(options);

		// Create main page container
		self.el = new Element('div.page.'+self.name);
	},

	load: function(){
		var self = this;

		// Create tab for page
		if(self.has_tab){
			var nav;

			if(self.parent_page && self.parent_page.navigation){
				nav = self.parent_page.navigation;
			}
			else {
				nav = App.getBlock('navigation');
			}

			self.tab = nav.addTab(self.name, {
				'href': App.createUrl(self.getPageUrl()),
				'title': self.title,
				'text': self.name.capitalize()
			});
		}

		if(self.sub_pages){
			self.loadSubPages();
		}

	},

	loadSubPages: function(){
		var self = this;

		var sub_pages = self.sub_pages;

		self.pages = new Element('div.pages').inject(self.el);

		self.sub_pages = [];
		sub_pages.each(function(class_name){
			var pg = new window[self.name.capitalize()+class_name](self, {});
			self.sub_pages[class_name] = pg;

			self.sub_pages.include({
				'order': pg.order,
				'name': class_name,
				'class': pg
			});
		});

		self.sub_pages.stableSort(self.sortPageByOrder).each(function(page){
			page['class'].load();
			self.fireEvent('load'+page.name);

			$(page['class']).inject(self.pages);
		});

	},

	open: function(action, params){
		var self = this;
		//p('Opening: ' +self.getName() + ', ' + action + ', ' + Object.toQueryString(params));

		try {
			var elements
			if(!self[action+'Action']){
				elements = self['defaultAction'](action, params);
			}
			else {
				elements = self[action+'Action'](params);
			}
			if(elements !== undefined){
				self.el.empty();
				self.el.adopt(elements);
			}

			App.getBlock('navigation').activate(self.name);
			self.fireEvent('opened');
		}
		catch (e){
			self.errorAction(e);
			self.fireEvent('error');
		}
	},

	openUrl: function(url){
		if(History.getPath() != url)
			History.push(url);
	},

	getPageUrl: function(){
		var self = this;
		return (self.parent_page && self.parent_page.getPageUrl ? self.parent_page.getPageUrl() + '/' : '') + self.name;
	},

	errorAction: function(e){
		p('Error, action not found', e);
	},

	getName: function(){
		return this.name;
	},

	show: function(){
		this.el.addClass('active');
	},

	hide: function(){
		this.el.removeClass('active');
	},

	toElement: function(){
		return this.el;
	}
});

var Page = {};
