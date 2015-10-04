var PageBase = new Class({

	Implements: [Options, Events],

	disable_pointer_onscroll: true,
	order: 1,
	has_tab: true,
	name: '',
	icon: null,

	parent_page: null,
	sub_pages: null,

	initialize: function(parent_page, options) {
		var self = this;

		self.parent_page = parent_page;
		self.setOptions(options);

		// Create main page container
		self.el = new Element('div', {
			'class': 'page ' + self.getPageClass() + (' level_' + (options.level || 0))
		}).grab(
			self.content = new Element('div.scroll_content')
		);

		// Stop hover events while scrolling
		if(self.options.disable_pointer_onscroll){
			App.addEvent('load', function(){
				requestTimeout(function(){
					if(!App.mobile_screen && !App.getOption('dev')){
						self.content.addEvent('scroll', self.preventHover.bind(self));
					}
				}, 100);
			});
		}
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
				'html': '<span>' + self.name.capitalize() + '</span>',
				'class': self.icon ? 'icon-' + self.icon : null
			});
		}

		if(self.sub_pages){
			self.loadSubPages();
		}

	},

	loadSubPages: function(){
		var self = this;

		var sub_pages = self.sub_pages;

		self.sub_pages = [];
		sub_pages.each(function(class_name){
			var pg = new window[self.name.capitalize()+class_name](self, {
				'level': 2
			});
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

			$(page['class']).inject(App.getPageContainer());
		});

	},

	sortPageByOrder: function(a, b){
		return (a.order || 100) - (b.order || 100);
	},

	open: function(action, params){
		var self = this;
		//p('Opening: ' +self.getName() + ', ' + action + ', ' + Object.toQueryString(params));

		try {
			var elements;
			if(!self[action+'Action']){
				elements = self.defaultAction(action, params);
			}
			else {
				elements = self[action+'Action'](params);
			}
			if(elements !== undefined){
				self.content.empty();
				self.content.adopt(elements);
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

	getPageClass: function(){
		var self = this;
		return (self.parent_page && self.parent_page.getPageClass ? self.parent_page.getPageClass() + '_' : '') + self.name;
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
		var self = this;

		self.el.removeClass('active');

		if(self.sub_pages){
			self.sub_pages.each(function(sub_page){
				sub_page['class'].hide();
			});
		}
	},

	preventHover: function(){
		var self = this;

		if(self.hover_timer) clearRequestTimeout(self.hover_timer);
		self.el.addClass('disable_hover');

		self.hover_timer = requestTimeout(function(){
			self.el.removeClass('disable_hover');
		}, 200);
	},

	toElement: function(){
		return this.el;
	}
});

var Page = {};
