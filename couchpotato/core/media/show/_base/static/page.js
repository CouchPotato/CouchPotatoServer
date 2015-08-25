Page.Shows = new Class({

	Extends: PageBase,

	name: 'shows',
	icon: 'show',
	sub_pages: ['Wanted'],
	default_page: 'Wanted',
	current_page: null,

	initialize: function(parent, options){
		var self = this;
		self.parent(parent, options);

		self.navigation = new BlockNavigation();
		$(self.navigation).inject(self.content, 'top');

		App.on('shows.enabled', self.toggleShows.bind(self));

	},

	defaultAction: function(action, params){
		var self = this;

		if(self.current_page){
			self.current_page.hide();

			if(self.current_page.list && self.current_page.list.navigation)
				self.current_page.list.navigation.dispose();
		}

		var route = new Route();
			route.parse(action);

		var page_name = route.getPage() != 'index' ? route.getPage().capitalize() : self.default_page;

		var page = self.sub_pages.filter(function(page){
			return page.name == page_name;
		}).pick()['class'];

		page.open(route.getAction() || 'index', params);
		page.show();

		if(page.list && page.list.navigation)
			page.list.navigation.inject(self.navigation);

		self.current_page = page;
		self.navigation.activate(page_name.toLowerCase());

	},

	toggleShows: function(notification) {
		document.body[notification.data === true ? 'addClass' : 'removeClass']('show_support');
	}

});
