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
						self.title_dropdown = new BlockMenu(self, {
							'class': 'title',
							'button_text': parent.getTitle() + (parent.get('year') ? ' (' + parent.get('year') + ')' : ''),
							'button_class': 'icon-dropdown'
						})
					),
					self.buttons = new Element('div.buttons')
				)
			)
		);

		self.addSection('description', new Element('div', {
			'text': parent.get('plot')
		}));


		// Title dropdown
		var titles = parent.get('info').titles;
		$(self.title_dropdown).addEvents({
			'click:relay(li a)': function(e, el){
				(e).stopPropagation();

				// Update category
				Api.request('movie.edit', {
					'data': {
						'id': parent.get('_id'),
						'default_title': el.get('text')
					}
				});

				$(self.title_dropdown).getElements('.icon-ok').removeClass('icon-ok');
				el.addClass('icon-ok');

				self.title_dropdown.button.set('text', el.get('text') + (parent.get('year') ? ' (' + parent.get('year') + ')' : ''));

			}
		});

		titles.each(function(t){
			self.title_dropdown.addLink(new Element('a', {
				'text': t,
				'class': parent.get('title') == t ? 'icon-ok' : ''
			}));
		});

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
