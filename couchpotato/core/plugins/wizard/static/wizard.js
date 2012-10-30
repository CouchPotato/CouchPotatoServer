Page.Wizard = new Class({

	Extends: Page.Settings,

	name: 'wizard',
	has_tab: false,
	wizard_only: true,

	headers: {
		'welcome': {
			'title': 'Welcome to the new CouchPotato',
			'description': 'To get started, fill in each of the following settings as much as your can. <br />Maybe first start with importing your movies from the previous CouchPotato',
			'content': new Element('div', {
				'styles': {
					'margin': '0 0 0 30px'
				}
			}).adopt(
				new Element('div', {
					'html': 'Select the <strong>data.db</strong>. It should be in your CouchPotato root directory.'
				}),
				self.import_iframe = new Element('iframe', {
					'styles': {
						'height': 40,
						'width': 300,
						'border': 0,
						'overflow': 'hidden'
					}
				})
			),
			'event': function(){
				self.import_iframe.set('src', Api.createUrl('v1.import'))
			}
		},
		'general': {
			'title': 'General',
			'description': 'If you want to access CP from outside your local network, you better secure it a bit with a username & password.'
		},
		'downloaders': {
			'title': 'What download apps are you using?',
			'description': 'CP needs an external download app to work with. Choose one below. For more downloaders check settings after you have filled in the wizard. If your download app isn\'t in the list, use the default Blackhole.'
		},
		'providers': {
			'title': 'Are you registered at any of these sites?',
			'description': 'CP uses these sites to search for movies. A few free are enabled by default, but it\'s always better to have a few more. Check settings for the full list of available providers.',
			'include': ['nzb_providers', 'torrent_providers']
		},
		'renamer': {
			'title': 'Move & rename the movies after downloading?',
			'description': 'The coolest part of CP is that it can move and organize your downloaded movies automagically. Check settings and you can even download trailers, subtitles and other data when it has finished downloading. It\'s awesome!'
		},
		'automation': {
			'title': 'Easily add movies to your wanted list!',
			'description': 'You can easily add movies from your favorite movie site, like IMDB, Rotten Tomatoes, Apple Trailers and more. Just install the userscript or drag the bookmarklet to your browsers bookmarks.' +
				'<br />Once installed, just click the bookmarklet on a movie page and watch the magic happen ;)',
			'content': function(){
				return App.createUserscriptButtons().setStyles({
					'background-image': "url('"+Api.createUrl('static/userscript/userscript.png')+"')"
				})
			}
		},
		'finish': {
			'title': 'Finishing Up',
			'description': 'Are you done? Did you fill in everything as much as possible?' +
				'<br />Be sure to check the settings to see what more CP can do!<br /><br />' +
				'<div class="wizard_support">After you\'ve used CP for a while, and you like it (which of course you will), consider supporting CP. Maybe even by writing some code. <br />Or by getting a subscription at <a href="https://usenetserver.com/partners/?a_aid=couchpotato&a_bid=3f357c6f">Usenet Server</a> or <a href="http://www.newshosting.com/partners/?a_aid=couchpotato&a_bid=a0b022df">Newshosting</a>.</div>',
			'content': new Element('div').adopt(
				new Element('a.button.green', {
					'styles': {
						'margin-top': 20
					},
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
	groups: ['welcome', 'general', 'downloaders', 'searcher', 'providers', 'renamer', 'automation', 'finish'],

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

		self.groups.each(function(group, nr){

			if(self.headers[group]){
				group_container = new Element('.wgroup_'+group, {
					'styles': {
						'opacity': 0.2
					},
					'tween': {
						'duration': 350
					}
				});

				if(self.headers[group].include){
					self.headers[group].include.each(function(inc){
						group_container.addClass('wgroup_'+inc);
					})
				}

				var content = self.headers[group].content
				group_container.adopt(
					new Element('h1', {
						'text': self.headers[group].title
					}),
					self.headers[group].description ? new Element('span.description', {
						'html': self.headers[group].description
					}) : null,
					content ? (typeOf(content) == 'function' ? content() : content) : null
				).inject(form);
			}

			var tab_navigation = tabs.getElement('.t_'+group);

			if(!tab_navigation && self.headers[group] && self.headers[group].include){
				tab_navigation = []
				self.headers[group].include.each(function(inc){
					tab_navigation.include(tabs.getElement('.t_'+inc));
				})
			}

			if(tab_navigation && group_container){
				tabs.adopt(tab_navigation); // Tab navigation

				if(self.headers[group] && self.headers[group].include){

					self.headers[group].include.each(function(inc){
						self.el.getElement('.tab_'+inc).inject(group_container);
					})

					new Element('li.t_'+group).adopt(
						new Element('a', {
							'href': App.createUrl('wizard/'+group),
							'text': (self.headers[group].label || group).capitalize()
						})
					).inject(tabs);

				}
				else
					self.el.getElement('.tab_'+group).inject(group_container); // Tab content

				if(tab_navigation.getElement && self.headers[group]){
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

			if(self.headers[group] && self.headers[group].event)
				self.headers[group].event.call()
		});

		// Remove toggle
		self.el.getElement('.advanced_toggle').destroy();

		// Hide retention
		self.el.getElement('.tab_searcher').hide();
		self.el.getElement('.t_searcher').hide();
		self.el.getElement('.t_nzb_providers').hide();
		self.el.getElement('.t_torrent_providers').hide();

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