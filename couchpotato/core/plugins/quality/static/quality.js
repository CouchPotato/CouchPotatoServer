var QualityBase = new Class({

	tab: '',
	content: '',

	setup: function(data){
		var self = this;

		self.qualities = data.qualities;

		self.profiles = {}
		Object.each(data.profiles, self.createProfilesClass.bind(self));

		App.addEvent('load', self.addSettings.bind(self))

	},

	getProfile: function(id){
		return this.profiles[id]
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
					'click': function(){
						var profile = self.createProfilesClass();
						$(profile).inject(self.profile_container, 'top')
					}
				}
			}),
			self.profile_container = new Element('div.container')
		)

		Object.each(self.profiles, function(profile){
			if(!profile.isCore())
				$(profile).inject(self.profile_container, 'top')
		})

	},

	createProfilesClass: function(data){
		var self = this;

		if(data){
			return self.profiles[data.id] = new Profile(data);
		}
		else {
			var data = {
				'id': randomString()
			}
			return self.profiles[data.id] = new Profile(data);
		}
	},

	/**
	 * Sizes
	 */
	createSizes: function(){
		var self = this;

		var group = self.settings.createGroup({
			'label': 'Sizes',
			'description': 'Discriptions',
			'advanced': true
		}).inject(self.content)
		
		new Element('div.item.header').adopt(
			new Element('span.label', {'text': 'Quality'}),
			new Element('span.min', {'text': 'Min'}),
			new Element('span.max', {'text': 'Max'})
		).inject(group)
		
		Object.each(self.qualities, function(quality){
			new Element('div.item').adopt(
				new Element('span.label', {'text': quality.label}),
				new Element('input.min', {'value': quality.size_min}),
				new Element('input.max', {'value': quality.size_max})
			).inject(group)
		})
		
		p(group)
		
	}

});

window.Quality = new QualityBase();
