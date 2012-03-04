Block.More = new Class({

	Extends: BlockBase,

	create: function(){
		var self = this;

		self.el = new Element('div.more_menu').adopt(
			self.more_option_ul = new Element('ul').adopt(
				new Element('li').adopt(
					new Element('a.orange', {
						'text': 'Restart',
						'events': {
							'click': App.restart.bind(App)
						}
					})
				),
				new Element('li').adopt(
					new Element('a.red', {
						'text': 'Shutdown',
						'events': {
							'click': App.shutdown.bind(App)
						}
					})
				)
			),
			new Element('a.button.onlay', {
				'events': {
					'click': function(){
						self.more_option_ul.toggleClass('show')

						if(self.more_option_ul.hasClass('show'))
							this.addEvent('outerClick', function(){
								self.more_option_ul.removeClass('show')
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
		var self = this

		return new Element('li').adopt(tab).inject(self.more_option_ul, position || 'bottom')

	}

});