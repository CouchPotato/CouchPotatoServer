var MovieDetails = new Class({

	Extends: BlockBase,

	sections: null,

	initialize: function(parent, options){
		var self = this;

		self.sections = {};

		self.el = new Element('div',{
			'class': 'page active movie_details level_' + (options.level || 0)
		}).adopt(
			self.overlay = new Element('div.overlay', {
				'events': {
					'click': self.close.bind(self)
				}
			}).grab(
				new Element('a.close.icon-left-arrow')
			),
			self.content = new Element('div.content').grab(
				new Element('h1', {
					'text': parent.getTitle() + (parent.get('year') ? ' (' + parent.get('year') + ')' : '')
				})
			)
		);

		self.addSection('description', new Element('div', {
			'text': parent.get('plot')
		}));

	},

	addSection: function(name, section_el){
		var self = this;
		name = name.toLowerCase();

		self.content.grab(
			self.sections[name] = new Element('div', {
				'class': 'section section_' + name
			}).grab(section_el)
		);
	},

	close: function(){
		var self = this;

		self.el.dispose();
	}

});
