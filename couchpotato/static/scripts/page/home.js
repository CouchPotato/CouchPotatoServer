Page.Home = new Class({

	Extends: PageBase,

	name: 'home',
	title: 'Manage new stuff for things and such',

	indexAction: function () {
		var self = this;

		if(self.soon_list){

			// Reset lists
			self.available_list.update();
			self.late_list.update();

			return;
		}

		self.chain = new Chain();
		self.chain.chain(
			self.createAvailable.bind(self),
			self.createSoon.bind(self),
			self.createSuggestionsChartsMenu.bind(self),
			self.createSuggestions.bind(self),
			self.createCharts.bind(self),
			self.createLate.bind(self)
		);

		self.chain.callChain();

	},

	createAvailable: function(){
		var self = this;

		self.available_list = new MovieList({
			'navigation': false,
			'identifier': 'snatched',
			'load_more': false,
			'view': 'list',
			'actions': [MA.IMDB, MA.Trailer, MA.Release, MA.Refresh, MA.Delete],
			'title': 'Snatched & Available',
			'description': 'These movies have been snatched or have finished downloading',
			'on_empty_element': new Element('div').adopt(
				new Element('h2', {'text': 'Snatched & Available'}),
				new Element('span', {
					'html': 'No snatched movies or anything!? Damn.. <a>Maybe add a movie.</a>',
					'events': {
						'click': function(){
							$(document.body).getElement('.search_form input').focus();
						}
					}
				})
			),
			'filter': {
				'release_status': 'snatched,seeding,missing,available,downloaded'
			},
			'limit': null,
			'onLoaded': function(){
				self.chain.callChain();
			},
			'onMovieAdded': function(notification){

				// Track movie added
				var after_search = function(data){
					if(notification.data._id != data.data._id) return;

					// Force update after search
					self.available_list.update();
					App.off('movie.searcher.ended', after_search);
				};
				App.on('movie.searcher.ended', after_search);

			}
		});

		$(self.available_list).inject(self.el);

	},

	createSoon: function(){
		var self = this;

		// Coming Soon
		self.soon_list = new MovieList({
			'navigation': false,
			'identifier': 'soon',
			'limit': 12,
			'title': 'Available soon',
			'description': 'These are being searched for and should be available soon as they will be released on DVD in the next few weeks.',
			'filter': {
				'random': true
			},
			'actions': [MA.IMDB, MA.Refresh],
			'load_more': false,
			'view': 'thumbs',
			'force_view': true,
			'api_call': 'dashboard.soon',
			'onLoaded': function(){
				self.chain.callChain();
			}
		});

		// Make all thumbnails the same size
		self.soon_list.addEvent('loaded', function(){
			var images = $(self.soon_list).getElements('.poster, .no_thumbnail'),
				timer,
				highest = 100;

			images.each(function(img){
				img.addEvent('load', function(){
					var height = img.getSize().y;
					if(!highest || highest < height){
						highest = height;
						if(timer) clearTimeout(timer);
						timer = (function(){
							images.setStyle('height', highest);
						}).delay(50);
					}
				});
			});

			$(window).addEvent('resize', function(){
				if(timer) clearTimeout(timer);
				timer = (function(){
					var highest = 100;
					images.each(function(img){
						img.setStyle('height', null);
						var height = img.getSize().y;
						if(!highest || highest < height)
							highest = height;
					});
					images.setStyle('height', highest);
				}).delay(300);
			});

		});

		$(self.soon_list).inject(self.el);

	},

	createSuggestions: function(){
		var self = this;

		// Suggest
		self.suggestion_list = new SuggestList({
			'onLoaded': function(){
				self.chain.callChain();
			}
		});

		$(self.suggestion_list).inject(self.el);

	},

	createCharts: function(){
		var self = this;

		// Charts
		self.charts = new Charts({
			'onCreated': function(){
				self.chain.callChain();
			}
		});

		$(self.charts).inject(self.el);

	},

	createSuggestionsChartsMenu: function(){
		var self = this;

		self.el_toggle_menu_suggestions = new Element('a.toggle_suggestions.active', {
                'href': '#',
                'events': { 'click': function(e) {
                        e.preventDefault();
                        self.toggleSuggestionsCharts('suggestions');
                    }
                }
            }).grab( new Element('h2', {'text': 'Suggestions'}));

        self.el_toggle_menu_charts = new Element('a.toggle_charts', {
                'href': '#',
                'events': { 'click': function(e) {
                        e.preventDefault();
                        self.toggleSuggestionsCharts('charts');
                    }
                }
            }).grab( new Element('h2', {'text': 'Charts'}));

        self.el_toggle_menu = new Element('div.toggle_menu').grab(
                self.el_toggle_menu_suggestions
            ).grab(
                self.el_toggle_menu_charts
            );

        var menu_selected = Cookie.read('suggestions_charts_menu_selected');
        if( menu_selected === null ) menu_selected = 'suggestions';
        self.toggleSuggestionsCharts( menu_selected );

		self.el_toggle_menu.inject(self.el);

		self.chain.callChain();

	},

	toggleSuggestionsCharts: function(menu_id){
	    var self = this;

	    switch(menu_id) {
            case 'suggestions':
                if($(self.suggestion_list)) $(self.suggestion_list).show();
                self.el_toggle_menu_suggestions.addClass('active');
                if($(self.charts)) $(self.charts).hide();
                self.el_toggle_menu_charts.removeClass('active');
                break;
            case 'charts':
                if($(self.charts)) $(self.charts).show();
                self.el_toggle_menu_charts.addClass('active');
                if($(self.suggestion_list)) $(self.suggestion_list).hide();
                self.el_toggle_menu_suggestions.removeClass('active');
                break;
        }

		Cookie.write('suggestions_charts_menu_selected', menu_id, {'duration': 365});
	},

	createLate: function(){
		var self = this;

		// Still not available
		self.late_list = new MovieList({
			'navigation': false,
			'identifier': 'late',
			'limit': 50,
			'title': 'Still not available',
			'description': 'Try another quality profile or maybe add more providers in <a href="' + App.createUrl('settings/searcher/providers/') + '">Settings</a>.',
			'filter': {
				'late': true
			},
			'loader': false,
			'load_more': false,
			'view': 'list',
			'actions': [MA.IMDB, MA.Trailer, MA.Edit, MA.Refresh, MA.Delete],
			'api_call': 'dashboard.soon',
			'onLoaded': function(){
				self.chain.callChain();
			}
		});

		$(self.late_list).inject(self.el);

	}

});
