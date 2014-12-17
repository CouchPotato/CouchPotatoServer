var MovieDetails = new Class({

	Extends: BlockBase,

	sections: null,

	initialize: function(parent, options){
		var self = this;

		self.sections = {};

		self.el = new Element('div',{
			'class': 'page active movie_details level_' + (options.level || 0)
		}).adopt(
			self.overlay = new Element('div.overlay').grab(
				new Element('a.close.icon-left-arrow')
			),
			self.content = new Element('div.content').grab(
				new Element('h1', {
					'text': 'Title'
				})
			)
		);

		self.addSection('description', new Element('div', {
			'text': 'Description'
		}));

	},

	addSection: function(name, section_el){
		var self = this;

		self.content.grab(
			self.sections[name] = new Element('div', {
				'class': 'section section_' + name
			}).grab(section_el)
		);
	}

});