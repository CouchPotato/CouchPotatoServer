var QualityBase = new Class({

	tab: '',
	content: '',

	setup: function(data){
		var self = this;

		self.qualities = data.qualities;

		self.profiles = [];
		Array.each(data.profiles, self.createProfilesClass.bind(self));

		App.addEvent('loadSettings', self.addSettings.bind(self))

	},

	getProfile: function(id){
		return this.profiles.filter(function(profile){
			return profile.data._id == id
		}).pick()
	},

	// Hide items when getting profiles
	getActiveProfiles: function(){
		return Array.filter(this.profiles, function(profile){
			return !profile.data.hide
		});
	},

	getQuality: function(identifier){
		return this.qualities.filter(function(q){
			return q.identifier == identifier;
		}).pick();
	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings');
		self.settings.addEvent('create', function(){
			var tab = self.settings.createSubTab('profile', {
				'label': 'Quality',
				'name': 'profile',
				'subtab_label': 'Qualities'
			}, self.settings.tabs.searcher ,'searcher');

			self.tab = tab.tab;
			self.content = tab.content;

			self.createProfiles();
			self.createProfileOrdering();
			self.createSizes();

		})

	},

	/**
	 * Profiles
	 */
	createProfiles: function(){
		var self = this;

		var non_core_profiles = Array.filter(self.profiles, function(profile){ return !profile.isCore() });
		var count = non_core_profiles.length;

		self.settings.createGroup({
			'label': 'Quality Profiles',
			'description': 'Create your own profiles with multiple qualities.'
		}).inject(self.content).adopt(
			self.profile_container = new Element('div.container'),
			new Element('a.add_new_profile', {
				'text': count > 0 ? 'Create another quality profile' : 'Click here to create a quality profile.',
				'events': {
					'click': function(){
						var profile = self.createProfilesClass();
						$(profile).inject(self.profile_container)
					}
				}
			})
		);

		// Add profiles, that aren't part of the core (for editing)
		Array.each(non_core_profiles, function(profile){
			$(profile).inject(self.profile_container)
		});

	},

	createProfilesClass: function(data){
		var self = this;

		var data = data || {'id': randomString()};
		var profile = new Profile(data);
		self.profiles.include(profile);

		return profile;
	},

	createProfileOrdering: function(){
		var self = this;

		var profile_list;
		self.settings.createGroup({
			'label': 'Profile Defaults',
			'description':  '(Needs refresh \'' +(App.isMac() ? 'CMD+R' : 'F5')+ '\' after editing)'
		}).adopt(
			new Element('.ctrlHolder#profile_ordering').adopt(
				new Element('label[text=Order]'),
				profile_list = new Element('ul'),
				new Element('p.formHint', {
					'html': 'Change the order the profiles are in the dropdown list. Uncheck to hide it completely.<br />First one will be default.'
				})
			)
		).inject(self.content);

		Array.each(self.profiles, function(profile){
			var check;
			new Element('li', {'data-id': profile.data._id}).adopt(
				check = new Element('input.inlay[type=checkbox]', {
					'checked': !profile.data.hide,
					'events': {
						'change': self.saveProfileOrdering.bind(self)
					}
				}),
				new Element('span.profile_label', {
					'text': profile.data.label
				}),
				new Element('span.handle')
			).inject(profile_list);

			new Form.Check(check);

		});

		// Sortable
		self.profile_sortable = new Sortables(profile_list, {
			'revert': true,
			'handle': '',
			'opacity': 0.5,
			'onComplete': self.saveProfileOrdering.bind(self)
		});

	},

	saveProfileOrdering: function(){
		var self = this;

		var ids = [];
		var hidden = [];

		self.profile_sortable.list.getElements('li').each(function(el, nr){
			ids.include(el.get('data-id'));
			hidden[nr] = +!el.getElement('input[type=checkbox]').get('checked');
		});

		Api.request('profile.save_order', {
			'data': {
				'ids': ids,
				'hidden': hidden
			}
		});

	},

	/**
	 * Sizes
	 */
	createSizes: function(){
		var self = this;

		var group = self.settings.createGroup({
			'label': 'Sizes',
			'description': 'Edit the minimal and maximum sizes (in MB) for each quality.',
			'advanced': true,
			'name': 'sizes'
		}).inject(self.content);


		new Element('div.item.head.ctrlHolder').adopt(
			new Element('span.label', {'text': 'Quality'}),
			new Element('span.min', {'text': 'Min'}),
			new Element('span.max', {'text': 'Max'})
		).inject(group);

		Array.each(self.qualities, function(quality){
			new Element('div.ctrlHolder.item').adopt(
				new Element('span.label', {'text': quality.label}),
				new Element('input.min.inlay[type=text]', {
					'value': quality.size_min,
					'events': {
						'keyup': function(e){
							self.changeSize(quality.identifier, 'size_min', e.target.get('value'))
						}
					}
				}),
				new Element('input.max.inlay[type=text]', {
					'value': quality.size_max,
					'events': {
						'keyup': function(e){
							self.changeSize(quality.identifier, 'size_max', e.target.get('value'))
						}
					}
				})
			).inject(group)
		});

	},

	size_timer: {},
	changeSize: function(identifier, type, value){
		var self = this;

		if(self.size_timer[identifier + type]) clearTimeout(self.size_timer[identifier + type]);

		self.size_timer[identifier + type] = (function(){
			Api.request('quality.size.save', {
				'data': {
					'identifier': identifier,
					'value_type': type,
					'value': value
				}
			});
		}).delay(300)

	}

});

window.Quality = new QualityBase();
