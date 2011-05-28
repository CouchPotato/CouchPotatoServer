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
			self.header = new Element('h4', {'text': data.label}),
			new Element('span.delete.icon', {
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('div', {
				'class': 'ctrlHolder'
			}).adopt(
				new Element('label', {'text':'Name'}),
				new Element('input.label.textInput.large', {
					'type':'text',
					'value': data.label,
					'events': {
						'keyup': function(){
							self.header.set('text', this.get('value'))
						}
					}
				})
			),
			new Element('div.ctrlHolder').adopt(
				new Element('label', {'text':'Wait'}),
				new Element('input.wait_for.textInput.xsmall', {
					'type':'text',
					'value': data.types && data.types.length > 0 ? data.types[0].wait_for : 0
				}),
				new Element('span', {'text':' day(s) for better quality.'})
			),
			new Element('div.ctrlHolder').adopt(
				new Element('label', {'text': 'Qualities'}),
				new Element('div.head').adopt(
					new Element('span.quality_type', {'text': 'Search for'}),
					new Element('span.finish', {'html': '<acronym title="Won\'t download anything else if it has found this quality.">Finish</acronym>'})
				),
				self.type_container = new Element('ol.types'),
				new Element('a.addType', {
					'text': 'Add another quality to search for.',
					'href': '#',
					'events': {
						'click': self.addType.bind(self)
					}
				})
			)
		);

		self.makeSortable()

		if(data.types)
			Object.each(data.types, self.addType.bind(self))
	},

	save: function(delay){
		var self = this;

		if(self.save_timer) clearTimeout(self.save_timer);
		self.save_timer = (function(){

			var data = self.getData();
			if(data.types.length < 2) return;

			Api.request('profile.save', {
				'data': self.getData(),
				'useSpinner': true,
				'spinnerOptions': {
					'target': self.el
				},
				'onComplete': function(json){
					if(json.success){
						self.data = json.profile
					}
				}
			});
		}).delay(delay, self)

	},

	getData: function(){
		var self = this;

		var data = {
			'id' : self.data.id,
			'label' : self.el.getElement('.label').get('value'),
			'wait_for' : self.el.getElement('.wait_for').get('value'),
			'types': []
		}

		Array.each(self.type_container.getElements('.type'), function(type){
			if(!type.hasClass('deleted'))
				data.types.include({
					'quality_id': type.getElement('select').get('value'),
					'finish': +type.getElement('input[type=checkbox]').checked
				});
		})

		return data
	},

	addType: function(data){
		var self = this;

		var t = new Profile.Type(data);
		$(t).inject(self.type_container);
		self.sortable.addItems($(t));

		self.types.include(t);

	},

	del: function(){
		var self = this;

        if(!confirm('Are you sure you want to delete this profile?')) return

		Api.request('profile.delete', {
			'data': {
				'id': self.data.id
			},
			'useSpinner': true,
			'spinnerOptions': {
				'target': self.el
			},
			'onComplete': function(json){
				if(json.success)
					self.el.destroy();
				else
					alert(json.message)
			}
		});
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

Profile.Type = Class({

	deleted: false,

	initialize: function(data){
		var self = this;

		self.data = data;
		self.create();

	},

	create: function(){
		var self = this;
		var data = self.data;

		self.el = new Element('li.type').adopt(
			new Element('span.quality_type').adopt(
				self.fillQualities()
			),
			new Element('span.finish').adopt(
				self.finish = new Element('input', {
					'type':'checkbox',
					'class':'finish',
					'checked': data.finish
				})
			),
			new Element('span.delete.icon', {
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('span.handle')
		)

	},

	fillQualities: function(){
		var self = this;

		self.qualities = new Element('select');

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

	del: function(){
		var self = this;

		self.el.addClass('deleted');
		self.el.hide();
		self.deleted = true;
	},

	toElement: function(){
		return this.el;
	}

})