Block.Menu = new Class({

	Extends: BlockBase,

	options: {
		'class': 'menu'
	},

	create: function(){
		var self = this;

		self.el = new Element('div', {
			'class': 'more_menu '+self.options['class']
		}).adopt(
			self.wrapper = new Element('div.wrapper').adopt(
				self.more_option_ul = new Element('ul')
			),
			self.button = new Element('a.button' + (self.options.button_class ? '.' + self.options.button_class : ''), {
				'events': {
					'click': function(){
						self.el.toggleClass('show');
						self.fireEvent(self.el.hasClass('show') ? 'open' : 'close');

						if(self.el.hasClass('show')){
							self.el.addEvent('outerClick', self.removeOuterClick.bind(self));
							this.addEvent('outerClick', function(e){
								if(e.target.get('tag') != 'input')
									self.removeOuterClick()
							})
						}
						else
							self.removeOuterClick()

					}
				}
			})
		)

	},

	removeOuterClick: function(){
		var self = this;

		self.el.removeClass('show');
		self.el.removeEvents('outerClick');

		self.button.removeEvents('outerClick');
	},

	addLink: function(tab, position){
		var self = this;
		return new Element('li').adopt(tab).inject(self.more_option_ul, position || 'bottom');
	}

});