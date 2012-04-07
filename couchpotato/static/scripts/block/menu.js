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
			new Element('a.button.onlay', {
				'events': {
					'click': function(){
						self.el.toggleClass('show')
						self.fireEvent(self.el.hasClass('show') ? 'open' : 'close')

						if(self.el.hasClass('show'))
							this.addEvent('outerClick', function(){
								self.el.removeClass('show')
								this.removeEvents('outerClick');
							})
						else
							this.removeEvents('outerClick');

					}
				}
			})
		)

	},

	addLink: function(tab, position){
		var self = this;
		var el = new Element('li').adopt(tab).inject(self.more_option_ul, position || 'bottom');
		return el;
	}

});