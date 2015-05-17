var MovieDetails = new Class({

	Extends: BlockBase,

	sections: null,
	buttons: null,

	initialize: function(parent, options){
		var self = this;

		self.sections = {};

		var category = parent.get('category'),
			profile = parent.profile;

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
				new Element('div.head').adopt(
					new Element('h1').grab(
						new Element('span.icon-dropdown', {
							'data-change': 'title',
							'text': parent.getTitle() + (parent.get('year') ? ' (' + parent.get('year') + ')' : '')
						})
					),
					self.buttons = new Element('div.buttons')
				)
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

	addButton: function(button){
		var self = this;

		self.buttons.grab(button);
	},

	close: function(){
		var self = this;

		self.el.dispose();
	}

});
