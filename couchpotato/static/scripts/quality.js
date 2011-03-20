var QualityBase = new Class({

	tab: '',
	content: '',

	setup: function(data){
		var self = this;

		self.profiles = data.profiles;
		self.qualities = data.qualities;

		App.addEvent('load', self.addSettings.bind(self))

	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings')
		self.settings.addEvent('create', function(){
			var tab = self.settings.createTab('profile', {
				'label': 'Profile',
				'name': 'profile'
			});

			self.tab = tab.tab;
			self.content = tab.content;

			self.createProfiles();
			self.createOrdering();
			self.createSizes();

		})

	},

	/**
	 * Profiles
	 */
	createProfiles: function(){
		var self = this;

		self.settings.createGroup({
			'label': 'Custom',
			'description': 'Discriptions'
		}).inject(self.content).adopt(
			new Element('a.add_new', {
				'text': 'Create a new quality profile',
				'events': {
					'click': self.createNewProfile.bind(self)
				}
			}),
			self.profile_container = new Element('div.container')
		)

		Object.each(self.profiles, self.createNewProfile.bind(self))

	},

	createNewProfile: function(data, nr){
		var self = this;

		self.profiles[nr] = new Profile(data);
		$(self.profiles[nr]).inject(self.profile_container)

	},

	/**
	 * Ordering
	 */
	createOrdering: function(){
		var self = this;

		self.settings.createGroup({
			'label': 'Order',
			'description': 'Discriptions'
		}).inject(self.content)

	},

	/**
	 * Sizes
	 */
	createSizes: function(){
		var self = this;

		self.settings.createGroup({
			'label': 'Sizes',
			'description': 'Discriptions',
			'advanced': true
		}).inject(self.content)
	}

});
window.Quality = new QualityBase();

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

		self.el = new Element('div', {
			'class': 'profile'
		}).adopt(
			new Element('h4', {'text': data.label}),
			new Element('span.delete', {
				'html': 'del',
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
					'value': data.label
				})
			),
			new Element('div.ctrlHolder').adopt(
				new Element('label', {'text':'Wait'}),
				new Element('input.wait_for.textInput.xsmall', {
					'type':'text',
					'value': data.wait_for
				}),
				new Element('span', {'text':' day(s) for better quality.'})
			),
			new Element('div.ctrlHolder').adopt(
				new Element('label', {'text': 'Qualities'}),
				self.type_container = new Element('div.types').adopt(
					new Element('div.head').adopt(
						new Element('span.quality_type', {'text': 'Search for'}),
						new Element('span.finish', {'html': '<acronym title="Won\'t download anything else if it has found this quality.">Finish</acronym>'})
					)
				),
				new Element('a.addType', {
					'text': 'Add another quality to search for.',
					'href': '#',
					'events': {
						'click': self.addType.bind(self)
					}
				})
			)
		);

		if(data.types)
			Object.each(data.types, self.addType.bind(self))
	},

	save: function(delay){
		var self = this;

		if(self.save_timer) clearTimeout(self.save_timer);
		self.save_timer = (function(){

			Api.request('profile.save', {
				'data': self.getData(),
				'useSpinner': true,
				'spinnerOptions': {
					'target': self.el
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
		
		Object.each(self.types, function(type){
			if(!type.deleted)
				data.types.include(type.getData());
		})
		
		return data
	},

	addType: function(data){
		var self = this;

		var t = new Profile.Type(data);
		$(t).inject(self.type_container);

		self.types.include(t);

	},

	del: function(){
		var self = this;

		Api.request('profile.delete', {
			'data': {
				'id': self.data.id
			},
			'useSpinner': true,
			'spinnerOptions': {
				'target': self.el
			},
			'onComplete': function(){
				self.el.destroy();
			}
		});
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

		self.el = new Element('div.type').adopt(
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
			new Element('span.delete', {
				'html': 'del',
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('span', {
				'class':'handle'
			})
		)

	},

	fillQualities: function(){
		var self = this;

		self.qualities = new Element('select');

		Object.each(Quality.qualities, function(q){
			new Element('option', {
				'text': q.label,
				'value': q.identifier
			}).inject(self.qualities)
		});

		self.qualities.set('value', self.data.quality);

		return self.qualities;

	},
	
	getData: function(){
		var self = this;
		
		return {
			'quality': self.qualities.get('value'),
			'finish': +self.finish.checked
		}
	},

	del: function(){
		var self = this;

		self.el.hide();
		self.deleted = true;
	},

	toElement: function(){
		return this.el;
	}

})
