var Profile = new Class({

	data: {},
	types: [],

	initialize: function(data){
		var self = this;

		self.data = data;
		self.types = [];

		self.create();

		self.el.addEvents({
			'change:relay(select, input[type=checkbox])': self.save.bind(self, 0),
			'keyup:relay(input[type=text])': self.save.bind(self, [300])
		});

	},

	create: function(){
		var self = this;

		var data = self.data;

		self.el = new Element('div.profile').adopt(
			self.delete_button = new Element('span.delete.icon', {
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('.quality_label.ctrlHolder').adopt(
				new Element('label', {'text':'Name'}),
				new Element('input.inlay', {
					'type':'text',
					'value': data.label,
					'placeholder': 'Profile name'
				})
			),
			new Element('div.wait_for.ctrlHolder').adopt(
				new Element('span', {'text':'Wait'}),
				new Element('input.inlay.xsmall', {
					'type':'text',
					'value': data.types && data.types.length > 0 ? data.types[0].wait_for : 0
				}),
				new Element('span', {'text':'day(s) for a better quality.'})
			),
			new Element('div.qualities.ctrlHolder').adopt(
				new Element('label', {'text': 'Search for'}),
				self.type_container = new Element('ol.types'),
				new Element('div.formHint', {
					'html': "Search these qualities (2 minimum), from top to bottom. Use the checkbox, to stop searching after it found this quality."
				})
			)
		);

		self.makeSortable()

		if(data.types)
			Object.each(data.types, self.addType.bind(self))
		else
			self.delete_button.hide();

		self.addType();
	},

	save: function(delay){
		var self = this;

		if(self.save_timer) clearTimeout(self.save_timer);
		self.save_timer = (function(){

			self.addType();

			var data = self.getData();
			if(data.types.length < 2)
				return;
			else
				self.delete_button.show();

			Api.request('profile.save', {
				'data': self.getData(),
				'useSpinner': true,
				'spinnerOptions': {
					'target': self.el
				},
				'onComplete': function(json){
					if(json.success){
						self.data = json.profile;
						self.type_container.getElement('li:first-child input[type=checkbox]')
							.set('checked', true)
							.getParent().addClass('checked');
					}
				}
			});

		}).delay(delay, self)

	},

	getData: function(){
		var self = this;

		var data = {
			'id' : self.data.id,
			'label' : self.el.getElement('.quality_label input').get('value'),
			'wait_for' : self.el.getElement('.wait_for input').get('value'),
			'types': []
		}

		Array.each(self.type_container.getElements('.type'), function(type){
			if(!type.hasClass('deleted') && type.getElement('select').get('value') > 0)
				data.types.include({
					'quality_id': type.getElement('select').get('value'),
					'finish': +type.getElement('input[type=checkbox]').checked
				});
		})

		return data
	},

	addType: function(data){
		var self = this;

		var has_empty = false;
		self.types.each(function(type){
			if($(type).hasClass('is_empty'))
				has_empty = true;
		});

		if(has_empty) return;

		var t = new Profile.Type(data, {
			'onChange': self.save.bind(self, 0)
		});
		$(t).inject(self.type_container);

		self.sortable.addItems($(t));

		self.types.include(t);

	},

	getTypes: function(){
		var self = this;

		return self.types.filter(function(type){
			return type.get('quality_id')
		});

	},

	del: function(){
		var self = this;

		var label = self.el.getElement('.quality_label input').get('value');
		var qObj = new Question('Are you sure you want to delete <strong>"'+label+'"</strong>?', 'Items using this profile, will be set to the default quality.', [{
			'text': 'Delete "'+label+'"',
			'class': 'delete',
			'events': {
				'click': function(e){
					(e).preventDefault();
					Api.request('profile.delete', {
						'data': {
							'id': self.data.id
						},
						'useSpinner': true,
						'spinnerOptions': {
							'target': self.el
						},
						'onComplete': function(json){
							if(json.success) {
								qObj.close();
								self.el.destroy();
							} else {
								alert(json.message);
							}
						}
					});
				}
			}
		}, {
			'text': 'Cancel',
			'cancel': true
		}]);

	},

	makeSortable: function(){
		var self = this;

		self.sortable = new Sortables(self.type_container, {
			'revert': true,
			//'clone': true,
			'handle': '.handle',
			'opacity': 0.5,
			'onComplete': self.save.bind(self, 300)
		});
	},

	get: function(attr){
		return this.data[attr]
	},

	isCore: function(){
		return this.data.core
	},

	toElement: function(){
		return this.el
	}

});

Profile.Type = new Class({

	Implements: [Events, Options],

	deleted: false,

	initialize: function(data, options){
		var self = this;
		self.setOptions(options);

		self.data = data || {};
		self.create();

		self.addEvent('change', function(){
			self.el[self.qualities.get('value') == '-1' ? 'addClass' : 'removeClass']('is_empty');
			self.deleted = self.qualities.get('value') == '-1';
		});

	},

	create: function(){
		var self = this;
		var data = self.data;

		self.el = new Element('li.type').adopt(
			new Element('span.quality_type').adopt(
				self.fillQualities()
			),
			new Element('span.finish').adopt(
				self.finish = new Element('input.inlay.finish[type=checkbox]', {
					'checked': data.finish,
					'events': {
						'change': function(e){
							if(self.el == self.el.getParent().getElement(':first-child')){
								self.finish_class.check();
								alert('Top quality always finishes the search')
								return;
							}

							self.fireEvent('change');
						}
					}
				})
			),
			new Element('span.delete.icon', {
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('span.handle')
		);

		self.el[self.data.quality_id > 0 ? 'removeClass' : 'addClass']('is_empty');

		self.finish_class = new Form.Check(self.finish);

	},

	fillQualities: function(){
		var self = this;

		self.qualities = new Element('select', {
			'events': {
				'change': self.fireEvent.bind(self, 'change')
			}
		}).adopt(
			new Element('option', {
				'text': '+ Add another quality',
				'value': -1
			})
		);

		Object.each(Quality.qualities, function(q){
			new Element('option', {
				'text': q.label,
				'value': q.id
			}).inject(self.qualities)
		});

		self.qualities.set('value', self.data.quality_id);

		return self.qualities;

	},

	getData: function(){
		var self = this;

		return {
			'quality_id': self.qualities.get('value'),
			'finish': +self.finish.checked
		}
	},

	get: function(key){
		return this.data[key];
	},

	del: function(){
		var self = this;

		self.el.addClass('deleted');
		self.el.hide();
		self.deleted = true;

		self.fireEvent('change');
	},

	toElement: function(){
		return this.el;
	}

})