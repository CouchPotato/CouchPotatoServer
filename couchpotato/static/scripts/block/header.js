var BlockHeader = new Class({

	Extends: BlockNavigation,

	create: function(){
		var self = this;

		self.parent();

		self.el.adopt(
			self.foldout = new Element('a.foldout.icon2.menu', {
				'events': {
					'click': self.toggleMenu.bind(self)
				}
			}).grab(new Element('span.overlay')),
			self.logo = new Element('a.logo', {
				'html': '<span>Couch</span><span>Potato</span>',
				'href': App.createUrl('')
			}),
			self.nav
		);

		new ScrollSpy({
			min: 400,
			onLeave: function(){
				self.backtotop.fade('out');
			},
			onEnter: function(){
				self.backtotop.fade('in');
			}
		});

		self.nav.addEvents({
			'click:relay(a)': function(){
				if($(document.body).getParent().hasClass('menu_shown'))
					self.toggleMenu();
			}
		});

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

	}

});
