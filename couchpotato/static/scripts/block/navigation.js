Block.Navigation = new Class({

	Extends: BlockBase,

	create: function(){
		var self = this;

		self.el = new Element('div.navigation').adopt(
			self.foldout = new Element('a.foldout.icon2.menu', {
				'events': {
					'click': self.toggleMenu.bind(self)
				}
			}).grab(new Element('span.overlay')),
			self.logo = new Element('a.logo', {
				'text': 'CouchPotato',
				'href': App.createUrl('')
			}),
			self.nav = new Element('ul'),
			self.backtotop = new Element('a.backtotop', {
				'text': 'back to top',
				'events': {
					'click': function(){
						window.scroll(0,0)
					}
				},
				'tween': {
					'duration': 100
				}
			})
		);

		new ScrollSpy({
			min: 400,
			onLeave: function(){
				self.backtotop.fade('out')
			},
			onEnter: function(){
				self.backtotop.fade('in')
			}
		});
		
		self.nav.addEvents({
			'click:relay(a)': function(){
				if($(document.body).getParent().hasClass('menu_shown'))
					self.toggleMenu();
			}
		})

	},

	addTab: function(name, tab){
		var self = this;

		return new Element('li.tab_'+(name || 'unknown')).grab(
			new Element('a', tab)
		).inject(self.nav)

	},

	toggleMenu: function(){
		var self = this,
			body = $(document.body),
			html = body.getParent();

		// Copy over settings menu
		if(!self.added){

			new Element('li.separator').inject(self.nav);
			body.getElements('.header .more_menu.menu li a, .header .more_menu.menu li span.separator').each(function(el, nr){
				if(nr <= 2) return;
				if(el.get('tag') == 'a')
					self.nav.grab(new Element('li').grab(el.clone().cloneEvents(el)));
				else	
					self.nav.grab(new Element('li.separator'));
			});

			self.added = true;
		}

		html.toggleClass('menu_shown');

	},

	activate: function(name){
		var self = this;

		self.nav.getElements('.active').removeClass('active');
		self.nav.getElements('.tab_'+name).addClass('active');

	}

});