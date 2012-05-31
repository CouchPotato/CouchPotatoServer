Block.Navigation = new Class({

	Extends: BlockBase,

	create: function(){
		var self = this;

		self.el = new Element('div.navigation').adopt(
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
		)

		new ScrollSpy({
			min: 400,
			onLeave: function(){
				self.backtotop.fade('out')
			},
			onEnter: function(){
				self.backtotop.fade('in')
			}
		})

	},

	addTab: function(name, tab){
		var self = this

		return new Element('li.tab_'+(name || 'unknown')).adopt(
			new Element('a', tab)
		).inject(self.nav)

	},

	activate: function(name){
		var self = this;

		self.nav.getElements('.active').removeClass('active');
		self.nav.getElements('.tab_'+name).addClass('active');

	}

});