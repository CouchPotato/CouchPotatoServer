var BlockMenu = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],

	options: {
		'class': 'menu'
	},

	lis: null,

	create: function(){
		var self = this;

		self.lis = [];

		self.shown = false;
		self.el = new Element('div', {
			'class': 'more_menu '+self.options['class']
		}).adopt(
			self.wrapper = new Element('div.wrapper').adopt(
				self.more_option_ul = new Element('ul')
			),
			self.button = new Element('a' + (self.options.button_class ? '.' + self.options.button_class : ''), {
				'text': self.options.button_text || '',
				'events': {
					'click': function(){

						if(!self.shown){
							dynamics.css(self.wrapper, {
								opacity: 0,
								scale: 0.1,
								display: 'block'
							});

							dynamics.animate(self.wrapper, {
								opacity: 1,
								scale: 1
							}, {
								type: dynamics.spring,
								frequency: 200,
								friction: 270,
								duration: 800
							});

							if(self.lis === null)
								self.lis = self.more_option_ul.getElements('> li').slice(0, 10);

							self.lis.each(function(li, nr){
								dynamics.css(li, {
									opacity: 0,
									translateY: 20
								});

								// Animate to final properties
								dynamics.animate(li, {
									opacity: 1,
									translateY: 0
								}, {
									type: dynamics.spring,
									frequency: 300,
									friction: 435,
									duration: 1000,
									delay: 100 + nr * 40
								});
							});

							self.shown = true;
						}
						else {
							self.hide();
						}

						self.fireEvent(self.shown ? 'open' : 'close');

						if(self.shown){
							self.el.addEvent('outerClick', self.removeOuterClick.bind(self));
							this.addEvent('outerClick', function(e) {
								if (e.target.get('tag') != 'input')
									self.removeOuterClick();
							});
						}
						else {
							self.removeOuterClick();
						}
					}
				}
			})
		);

	},

	hide: function(){
		var self = this;

		dynamics.animate(self.wrapper, {
			opacity: 0,
			scale: 0.1
		}, {
			type: dynamics.easeInOut,
			duration: 300,
			friction: 100,
			complete: function(){
				dynamics.css(self.wrapper, {
					display: 'none'
				});
			}
		});

		self.shown = false;

	},

	removeOuterClick: function(){
		var self = this;

		self.hide();
		self.el.removeClass('show');
		self.el.removeEvents('outerClick');

		self.button.removeEvents('outerClick');
	},

	addLink: function(tab, position){
		var self = this,
			li = new Element('li').adopt(tab).inject(self.more_option_ul, position || 'bottom');

		self.lis = null;

		return li;
	}

});
