var MultipleNewznab = new Class({

	input_types: ['use', 'host', 'api_key'],

	initialize: function(){
		var self = this;

		self.items = [];
		self.values = [];
		self.inputs = {};

		App.addEvent('load', self.addSettings.bind(self))

	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings')
		self.settings.addEvent('create', function(){

			self.fieldset = self.settings.tabs.providers.content.getElement('.section_newznab');

			self.input_types.each(function(name){
				self.inputs[name] = self.fieldset.getElement('input[name=newznab['+name+']]');
				var values = self.inputs[name].get('value').split(',');

				values.each(function(value, nr){
					if (!self.values[nr]) self.values[nr] = {};
					self.values[nr][name] = value.trim();
				});

				self.inputs[name].getParent().hide()
			});


			self.values.each(function(item, nr){
				self.createItem(item.use, item.host, item.api_key);
			});
			
			new Element('a.nice_button', {
				'text': 'Add new NewzNab provider',
				'events': {
					'click': function(e){
						(e).stop();
						
						self.createItem(1, '', '');
					}
				}
			}).inject(self.fieldset.getElement('h2'), 'after');

		})

	},

	createItem: function(use, host, api){
		var self = this;

		var checkbox = new Element('input[type=checkbox].use.inlay', {
			'checked': +use,
			'events': {
				'click': self.save.bind(self),
				'change': self.save.bind(self)
			}
		})

		var item = new Element('div.ctrlHolder').adopt(
			checkbox,
			new Element('input[type=text].host.inlay', {
				'value': host,
				'placeholder': 'Host',
				'events': {
					'keyup': self.save.bind(self),
					'change': self.save.bind(self)
				}
			}),
			new Element('input[type=text].api_key.inlay', {
				'value': api,
				'placeholder': 'Api hash key',
				'events': {
					'keyup': self.save.bind(self),
					'change': self.save.bind(self)
				}
			}),
			new Element('a.icon.delete', {
				'text': 'delete',
				'events': {
					'click': self.deleteItem.bind(self)
				}
			})
		).inject(self.fieldset);

		new Form.Check(checkbox, {
			'onChange': checkbox.fireEvent.bind(checkbox, 'change')
		});

		self.items.include(item)

	},

	save: function(){
		var self = this;

		var temp = {}
		self.items.each(function(item, nr){
			self.input_types.each(function(type){
				var input = item.getElement('input.'+type);

				if(!temp[type]) temp[type] = [];
				temp[type][nr] = input.get('type') == 'checkbox' ? +input.get('checked') : input.get('value').trim();

			})
		});

		self.input_types.each(function(name){
			self.inputs[name].set('value', temp[name].join(','));
			self.inputs[name].fireEvent('change');
		});


	},

	deleteItem: function(e){
		var self = this;
		(e).stop();

		var item = e.target.getParent();
		
		self.items.erase(item);
		item.destroy();

		self.save();
	}

});

window.MNewznab = new MultipleNewznab();
