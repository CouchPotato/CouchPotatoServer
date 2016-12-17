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
			self.delete_button = new Element('span.delete.icon-delete', {
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('.quality_label.ctrlHolder').adopt(
				new Element('label', {'text':'Name'}),
				new Element('input', {
					'type':'text',
					'value': data.label,
					'placeholder': 'Profile name'
				})
			),
			new Element('div.qualities.ctrlHolder').adopt(
				new Element('label', {'text': 'Search for'}),
				self.type_container = new Element('ol.types'),
				new Element('div.formHint', {
					'html': "Search these qualities (2 minimum), from top to bottom. Use the checkbox, to stop searching after it found this quality."
				})
			),
			new Element('div.wait_for.ctrlHolder').adopt(
				// "Wait the entered number of days for a checked quality, before downloading a lower quality release."
				new Element('span', {'text':'Wait'}),
				new Element('input.wait_for_input.xsmall', {
					'type':'text',
					'value': data.wait_for && data.wait_for.length > 0 ? data.wait_for[0] : 0
				}),
				new Element('span', {'text':'day(s) for a better quality '}),
				new Element('span.advanced', {'text':'and keep searching'}),

				// "After a checked quality is found and downloaded, continue searching for even better quality releases for the entered number of days."
				new Element('input.xsmall.stop_after_input.advanced', {
					'type':'text',
					'value': data.stop_after && data.stop_after.length > 0 ? data.stop_after[0] : 0
				}),
				new Element('span.advanced', {'text':'day(s) for a better (checked) quality.'}),

				// Minimum score of
				new Element('span.advanced', {'html':'<br/>Releases need a minimum score of'}),
				new Element('input.advanced.xsmall.minimum_score_input', {
					'size': 4,
					'type':'text',
					'value': data.minimum_score || 1
				})
			)
		);

		self.makeSortable();

		// Combine qualities and properties into types
		if(data.qualities){
			data.types = [];
			data.qualities.each(function(quality, nr){
				data.types.include({
					'quality': quality,
					'finish': data.finish[nr] || false,
					'3d': data['3d'] ? data['3d'][nr] || false : false
				});
			});
		}

		if(data.types)
			data.types.each(self.addType.bind(self));
		else
			self.delete_button.hide();

		self.addType();
	},

	save: function(delay){
		var self = this;

		if(self.save_timer) clearRequestTimeout(self.save_timer);
		self.save_timer = requestTimeout(function(){

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
						self.type_container.getElement('li:first-child input.finish[type=checkbox]')
							.set('checked', true)
							.getParent().addClass('checked');
					}
				}
			});

		}, delay);

	},

	getData: function(){
		var self = this;

		var data = {
			'id' : self.data._id,
			'label' : self.el.getElement('.quality_label input').get('value'),
			'wait_for' : self.el.getElement('.wait_for_input').get('value'),
			'stop_after' : self.el.getElement('.stop_after_input').get('value'),
			'minimum_score' : self.el.getElement('.minimum_score_input').get('value'),
			'types': []
		};

		Array.each(self.type_container.getElements('.type'), function(type){
			if(!type.hasClass('deleted') && type.getElement('select').get('value') != -1 && type.getElement('select').get('value') != "")
				data.types.include({
					'quality': type.getElement('select').get('value'),
					'finish': +type.getElement('input.finish[type=checkbox]').checked,
					'3d': +type.getElement('input.3d[type=checkbox]').checked
				});
		});

		return data;
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
			return type.get('quality');
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
							'id': self.data._id
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
		return this.data[attr];
	},

	isCore: function(){
		return this.data.core;
	},

	toElement: function(){
		return this.el;
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
			var has_quality = !(self.qualities.get('value') == '-1' || self.qualities.get('value') == '');
			self.el[!has_quality ? 'addClass' : 'removeClass']('is_empty');
			self.el[has_quality && Quality.getQuality(self.qualities.get('value')).allow_3d ? 'addClass': 'removeClass']('allow_3d');
			self.deleted = !has_quality;
		});

	},

	create: function(){
		var self = this;
		var data = self.data;

		self.el = new Element('li.type').adopt(
			new Element('span.quality_type.select_wrapper.icon-dropdown').grab(
				self.fillQualities()
			),
			self.finish_container = new Element('label.finish').adopt(
				self.finish = new Element('input.finish[type=checkbox]', {
					'checked': data.finish !== undefined ? data.finish : 1,
					'events': {
						'change': function(){
							if(self.el == self.el.getParent().getElement(':first-child')){
								alert('Top quality always finishes the search');
								return;
							}

							self.fireEvent('change');
						}
					}
				}),
				new Element('span.check_label[text=finish]')
			),
			self['3d_container'] = new Element('label.threed').adopt(
				self['3d'] = new Element('input.3d[type=checkbox]', {
					'checked': data['3d'] !== undefined ? data['3d'] : 0,
					'events': {
						'change': function(){
							self.fireEvent('change');
						}
					}
				}),
				new Element('span.check_label[text=3D]')
			),
			new Element('span.delete.icon-cancel', {
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('span.handle.icon-handle')
		);

		self.el[self.data.quality ? 'removeClass' : 'addClass']('is_empty');

		if(self.data.quality && Quality.getQuality(self.data.quality).allow_3d)
			self.el.addClass('allow_3d');

	},

	fillQualities: function(){
		var self = this;

		self.qualities = new Element('select', {
			'events': {
				'change': self.fireEvent.bind(self, 'change')
			}
		}).grab(
			new Element('option', {
				'text': '+ Add another quality',
				'value': -1
			})
		);

		Object.each(Quality.qualities, function(q){
			new Element('option', {
				'text': q.label,
				'value': q.identifier,
				'data-allow_3d': q.allow_3d
			}).inject(self.qualities);
		});

		self.qualities.set('value', self.data.quality || -1);

		return self.qualities;

	},

	getData: function(){
		var self = this;

		return {
			'quality': self.qualities.get('value'),
			'finish': +self.finish.checked,
			'3d': +self['3d'].checked
		};
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

});
