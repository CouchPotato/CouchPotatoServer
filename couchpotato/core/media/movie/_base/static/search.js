Block.Search.MovieItem = new Class({

	Implements: [Options, Events],

	initialize: function(info, options){
		var self = this;
		self.setOptions(options);

		self.info = info;
		self.alternative_titles = [];

		self.create();
	},

	create: function(){
		var self = this,
			info = self.info;

		self.el = new Element('div.media_result', {
			'id': info.imdb
		}).adopt(
			self.thumbnail = info.images && info.images.poster.length > 0 ? new Element('img.thumbnail', {
				'src': info.images.poster[0],
				'height': null,
				'width': null
			}) : null,
			self.options_el = new Element('div.options.inlay'),
			self.data_container = new Element('div.data', {
				'events': {
					'click': self.showOptions.bind(self)
				}
			}).adopt(
				self.info_container = new Element('div.info').adopt(
					new Element('h2').adopt(
						self.title = new Element('span.title', {
							'text': info.titles && info.titles.length > 0 ? info.titles[0] : 'Unknown'
						}),
						self.year = info.year ? new Element('span.year', {
							'text': info.year
						}) : null
					)
				)
			)
		)

		if(info.titles)
			info.titles.each(function(title){
				self.alternativeTitle({
					'title': title
				});
			})
	},

	alternativeTitle: function(alternative){
		var self = this;

		self.alternative_titles.include(alternative);
	},

	getTitle: function(){
		var self = this;
		try {
			return self.info.original_title ? self.info.original_title : self.info.titles[0];
		}
		catch(e){
			return 'Unknown';
		}
	},

	get: function(key){
		return this.info[key]
	},

	showOptions: function(){
		var self = this;

		self.createOptions();

		self.data_container.addClass('open');
		self.el.addEvent('outerClick', self.closeOptions.bind(self))

	},

	closeOptions: function(){
		var self = this;

		self.data_container.removeClass('open');
		self.el.removeEvents('outerClick')
	},

	add: function(e){
		var self = this;

		if(e)
			(e).preventDefault();

		self.loadingMask();

		Api.request('movie.add', {
			'data': {
				'identifier': self.info.imdb,
				'title': self.title_select.get('value'),
				'profile_id': self.profile_select.get('value'),
				'category_id': self.category_select.get('value')
			},
			'onComplete': function(json){
				self.options_el.empty();
				self.options_el.adopt(
					new Element('div.message', {
						'text': json.success ? 'Movie successfully added.' : 'Movie didn\'t add properly. Check logs'
					})
				);
				self.mask.fade('out');

				self.fireEvent('added');
			},
			'onFailure': function(){
				self.options_el.empty();
				self.options_el.adopt(
					new Element('div.message', {
						'text': 'Something went wrong, check the logs for more info.'
					})
				);
				self.mask.fade('out');
			}
		});
	},

	createOptions: function(){
		var self = this,
			info = self.info;

		if(!self.options_el.hasClass('set')){

			if(self.info.in_library){
				var in_library = [];
				self.info.in_library.releases.each(function(release){
					in_library.include(release.quality.label)
				});
			}

			self.options_el.grab(
				new Element('div', {
					'class': self.info.in_wanted && self.info.in_wanted.profile_id || in_library ? 'in_library_wanted' : ''
				}).adopt(
					self.info.in_wanted && self.info.in_wanted.profile_id ? new Element('span.in_wanted', {
						'text': 'Already in wanted list: ' + Quality.getProfile(self.info.in_wanted.profile_id).get('label')
					}) : (in_library ? new Element('span.in_library', {
						'text': 'Already in library: ' + in_library.join(', ')
					}) : null),
					self.title_select = new Element('select', {
						'name': 'title'
					}),
					self.profile_select = new Element('select', {
						'name': 'profile'
					}),
					self.category_select = new Element('select', {
						'name': 'category'
					}).grab(
						new Element('option', {'value': -1, 'text': 'None'})
					),
					self.add_button = new Element('a.button', {
						'text': 'Add',
						'events': {
							'click': self.add.bind(self)
						}
					})
				)
			);

			Array.each(self.alternative_titles, function(alt){
				new Element('option', {
					'text': alt.title
				}).inject(self.title_select)
			})


			// Fill categories
			var categories = CategoryList.getAll();

			if(categories.length == 0)
				self.category_select.hide();
			else {
				self.category_select.show();
				categories.each(function(category){
					new Element('option', {
						'value': category.data.id,
						'text': category.data.label
					}).inject(self.category_select);
				});
			}

			// Fill profiles
			var profiles = Quality.getActiveProfiles();
			if(profiles.length == 1)
				self.profile_select.hide();

			profiles.each(function(profile){
				new Element('option', {
					'value': profile.id ? profile.id : profile.data.id,
					'text': profile.label ? profile.label : profile.data.label
				}).inject(self.profile_select)
			});

			self.options_el.addClass('set');

			if(categories.length == 0 && self.title_select.getElements('option').length == 1 && profiles.length == 1 &&
				!(self.info.in_wanted && self.info.in_wanted.profile_id || in_library))
				self.add();

		}

	},

	loadingMask: function(){
		var self = this;

		self.mask = new Element('div.mask').inject(self.el).fade('hide')

		createSpinner(self.mask)
		self.mask.fade('in')

	},

	toElement: function(){
		return this.el
	}

});
