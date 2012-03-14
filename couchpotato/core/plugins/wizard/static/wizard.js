Page.Wizard = new Class({

	Extends: Page.Settings,

	name: 'wizard',
	has_tab: false,
	wizard_only: true,

	headers: {
		'welcome': {
			'title': 'Welcome to CouchPotato',
			'description': 'To get started, fill in each of the following settings as much as your can.'
		},
		'general': {
			'title': 'General',
			'description': 'If you want to access CP from outside your local network, you better secure it a bit with a username & password.'
		},
		'downloaders': {
			'title': 'What download apps are you using?',
			'description': 'If you don\'t have any of these listed, you have to use Blackhole. Or drop me a line, maybe I\'ll support your download app.'
		},
		'providers': {
			'title': 'Are you registered at any of these sites?',
			'description': 'CP uses these sites to search for movies. A few free are enabled by default, but it\'s always better to have a few more.'
		},
		'renamer': {
			'title': 'Move & rename the movies after downloading?',
			'description': ''
		},
		'finish': {
			'title': 'Finish Up',
			'description': 'Are you done? Did you fill in everything as much as possible? Yes, ok gogogo!',
			'content': new Element('div').adopt(
				new Element('a.button.green', {
					'text': 'I\'m ready to start the awesomeness, wow this button is big and green!',
					'events': {
						'click': function(e){
							(e).preventDefault();
							Api.request('settings.save', {
								'data': {
									'section': 'core',
									'name': 'show_wizard',
									'value': 0
								},
								'useSpinner': true,
								'spinnerOptions': {
									'target': self.el
								},
								'onComplete': function(){
									window.location = App.createUrl();
								}
							});
						}
					}
				})
			)
		}
	},
	groups: ['welcome', 'general', 'downloaders', 'searcher', 'providers', 'renamer', 'finish'],

	open: function(action, params){
		var self = this;

		if(!self.initialized){
			App.fireEvent('unload');
			App.getBlock('header').hide();

			self.parent(action, params);

			self.addEvent('create', function(){
				self.order();
			});

			self.initialized = true;

			self.scroll = new Fx.Scroll(document.body, {
				'transition': 'quint:in:out'
			});
		}
		else
			(function(){
				var sc = self.el.getElement('.wgroup_'+action);
				self.scroll.start(0, sc.getCoordinates().top-80);
			}).delay(1)
	},

	order: function(){
		var self = this;

		var form = self.el.getElement('.uniForm');
		var tabs = self.el.getElement('.tabs');

		self.groups.each(function(group){
			if(self.headers[group]){
				group_container = new Element('.wgroup_'+group, {
					'styles': {
						'opacity': 0.2
					},
					'tween': {
						'duration': 350
					}
				});
				group_container.adopt(
					new Element('h1', {
						'text': self.headers[group].title
					}),
					self.headers[group].description ? new Element('span.description', {
						'text': self.headers[group].description
					}) : null,
					self.headers[group].content ? self.headers[group].content : null
				).inject(form);
			}

			var tab_navigation = tabs.getElement('.t_'+group);
			if(tab_navigation && group_container){
				tab_navigation.inject(tabs); // Tab navigation
				self.el.getElement('.tab_'+group).inject(group_container); // Tab content
				if(self.headers[group]){
					var a = tab_navigation.getElement('a');
						a.set('text', (self.headers[group].label || group).capitalize());
						var url_split = a.get('href').split('wizard')[1].split('/');
						if(url_split.length > 3)
							a.set('href', a.get('href').replace(url_split[url_split.length-3]+'/', ''));

				}
			}
			else {
				new Element('li.t_'+group).adopt(
					new Element('a', {
						'href': App.createUrl('wizard/'+group),
						'text': (self.headers[group].label || group).capitalize()
					})
				).inject(tabs);
			}
		});

		// Remove toggle
		self.el.getElement('.advanced_toggle').destroy();

		// Hide retention
		self.el.getElement('.tab_searcher').hide();
		self.el.getElement('.t_searcher').hide();

		// Add pointer
		new Element('.tab_wrapper').wraps(tabs).adopt(
			self.pointer = new Element('.pointer', {
				'tween': {
					'transition': 'quint:in:out'
				}
			})
		);

		// Add nav
		var minimum = self.el.getSize().y-window.getSize().y;
		self.groups.each(function(group, nr){

			var g = self.el.getElement('.wgroup_'+group);
			if(!g || !g.isVisible()) return;
			var t = self.el.getElement('.t_'+group);
			if(!t) return;

			var func = function(){
				var ct = t.getCoordinates();
				self.pointer.tween('left', ct.left+(ct.width/2)-(self.pointer.getWidth()/2));
				g.tween('opacity', 1);
			}

			if(nr == 0)
				func();


			var ss = new ScrollSpy( {
				min: function(){
					var c = g.getCoordinates();
					var top = c.top-(window.getSize().y/2);
					return top > minimum ? minimum : top
				},
				max: function(){
					var c = g.getCoordinates();
					return c.top+(c.height/2)
				},
				onEnter: func,
				onLeave: function(){
					g.tween('opacity', 0.2)
				}
			});
		});

	}

});