var Movie = new Class({

	Extends: BlockBase,

	action: {},

	initialize: function(self, options, data){
		var self = this;

		self.data = data;
		self.view = options.view || 'thumbs';

		self.profile = Quality.getProfile(data.profile_id) || {};
		self.parent(self, options);
	},

	create: function(){
		var self = this;

		self.el = new Element('div.movie.inlay').adopt(
			self.select_checkbox = new Element('input[type=checkbox].inlay', {
				'events': {
					'change': function(){
						self.fireEvent('select')
					}
				}
			}),
			self.thumbnail = File.Select.single('poster', self.data.library.files),
			self.data_container = new Element('div.data.inlay.light', {
				'tween': {
					duration: 400,
					transition: 'quint:in:out',
					onComplete: self.fireEvent.bind(self, 'slideEnd')
				}
			}).adopt(
				self.info_container = new Element('div.info').adopt(
					self.title = new Element('div.title', {
						'text': self.getTitle()
					}),
					self.year = new Element('div.year', {
						'text': self.data.library.year || 'Unknown'
					}),
					self.rating = new Element('div.rating.icon', {
						'text': self.data.library.rating
					}),
					self.description = new Element('div.description', {
						'text': self.data.library.plot
					}),
					self.quality = new Element('div.quality', {
						'events': {
							'click': function(e){
								var releases = self.el.getElement('.actions .releases');
									if(releases)
										releases.fireEvent('click', [e])
							}
						}
					})
				),
				self.actions = new Element('div.actions')
			)
		);

		self.changeView(self.view);
		self.select_checkbox_class = new Form.Check(self.select_checkbox);

		// Add profile
		if(self.profile.data)
			self.profile.getTypes().each(function(type){

				var q = self.addQuality(type.quality_id || type.get('quality_id'));
				if(type.finish || type.get('finish'))
					q.addClass('finish');

			});

		// Add done releases
		Array.each(self.data.releases, function(release){

			var q = self.quality.getElement('.q_id'+ release.quality_id),
				status = Status.get(release.status_id);

			if(!q && status.identifier == 'snatched')
				var q = self.addQuality(release.quality_id)
			if (q)
				q.addClass(status.identifier);

		});

		Object.each(self.options.actions, function(action, key){
			self.actions.adopt(
				self.action[key.toLowerCase()] = new self.options.actions[key](self)
			)
		});

		if(!self.data.library.rating)
			self.rating.hide();

	},

	addQuality: function(quality_id){
		var self = this;

		var q = Quality.getQuality(quality_id);
		return new Element('span', {
			'text': q.label,
			'class': 'q_'+q.identifier + ' q_id' + q.id
		}).inject(self.quality);

	},

	getTitle: function(){
		var self = this;

		var titles = self.data.library.titles;

		var title = titles.filter(function(title){
			return title['default']
		}).pop()

		if(title)
			return self.getUnprefixedTitle(title.title)
		else if(titles.length > 0)
			return self.getUnprefixedTitle(titles[0].title)

		return 'Unknown movie'
	},

	getUnprefixedTitle: function(t){
		if(t.substr(0, 4).toLowerCase() == 'the ')
			t = t.substr(4) + ', The';
		return t;
	},

	slide: function(direction, el){
		var self = this;

		if(direction == 'in'){
			self.temp_view = self.view;
			self.changeView('thumbs')

			self.el.addEvent('outerClick', function(){
				self.changeView(self.temp_view)
				self.slide('out')
			})
			el.show();
			self.data_container.tween('right', 0, -840);
		}
		else {
			self.el.removeEvents('outerClick')

			self.addEvent('slideEnd:once', function(){
				self.el.getElements('> :not(.data):not(.poster)').hide();
			});

			self.data_container.tween('right', -840, 0);
		}
	},

	changeView: function(new_view){
		var self = this;

		self.el
			.removeClass(self.view+'_view')
			.addClass(new_view+'_view')

		self.view = new_view;
	},

	get: function(attr){
		return this.data[attr] || this.data.library[attr]
	},

	select: function(bool){
		var self = this;
		self.select_checkbox_class[bool ? 'check' : 'uncheck']()
	},

	isSelected: function(){
		return this.select_checkbox.get('checked');
	}

});

var MovieAction = new Class({

	class_name: 'action icon',

	initialize: function(movie){
		var self = this;
		self.movie = movie;

		self.create();
		if(self.el)
			self.el.addClass(self.class_name)
	},

	create: function(){},

	disable: function(){
		this.el.addClass('disable')
	},

	enable: function(){
		this.el.removeClass('disable')
	},

	toElement: function(){
		return this.el || null
	}

});

var IMDBAction = new Class({

	Extends: MovieAction,
	id: null,

	create: function(){
		var self = this;

		self.id = self.movie.get('identifier');

		self.el = new Element('a.imdb', {
			'title': 'Go to the IMDB page of ' + self.movie.getTitle(),
			'events': {
				'click': self.gotoIMDB.bind(self)
			}
		});

		if(!self.id) self.disable();
	},

	gotoIMDB: function(e){
		var self = this;
		(e).preventDefault();

		window.open('http://www.imdb.com/title/'+self.id+'/');
	}

});

var ReleaseAction = new Class({

	Extends: MovieAction,
	id: null,

	create: function(){
		var self = this;

		self.id = self.movie.get('identifier');

		self.el = new Element('a.releases.icon.download', {
			'title': 'Show the releases that are available for ' + self.movie.getTitle(),
			'events': {
				'click': self.show.bind(self)
			}
		});

	},

	show: function(e){
		var self = this;
		(e).preventDefault();

		if(!self.options_container){
			self.options_container = new Element('div.options').adopt(
				self.release_container = new Element('div.releases.table')
			).inject(self.movie, 'top');

			// Header
			new Element('div.item.head').adopt(
				new Element('span.name', {'text': 'Release name'}),
				new Element('span.quality', {'text': 'Quality'}),
				new Element('span.size', {'text': 'Size (MB)'}),
				new Element('span.age', {'text': 'Age'}),
				new Element('span.score', {'text': 'Score'}),
				new Element('span.provider', {'text': 'Provider'})
			).inject(self.release_container)

			Array.each(self.movie.data.releases, function(release){

				var status = Status.get(release.status_id),
					quality = Quality.getProfile(release.quality_id)

				new Element('div', {
					'class': 'item ' + status.identifier
				}).adopt(
					new Element('span.name', {'text': self.get(release, 'name'), 'title': self.get(release, 'name')}),
					new Element('span.quality', {'text': quality.get('label')}),
					new Element('span.size', {'text': (self.get(release, 'size') || 'unknown')}),
					new Element('span.age', {'text': self.get(release, 'age')}),
					new Element('span.score', {'text': self.get(release, 'score')}),
					new Element('span.provider', {'text': self.get(release, 'provider')}),
					new Element('a.download.icon', {
						'events': {
							'click': function(e){
								(e).preventDefault();
								self.download(release);
							}
						}
					}),
					new Element('a.delete.icon', {
						'events': {
							'click': function(e){
								(e).preventDefault();
								self.ignore(release);
								this.getParent('.item').toggleClass('ignored')
							}
						}
					})
				).inject(self.release_container)
			});

		}

		self.movie.slide('in', self.options_container);
	},

	get: function(release, type){
		var self = this;

		return (release.info.filter(function(info){
			return type == info.identifier
		}).pick() || {}).value
	},

	download: function(release){
		var self = this;

		Api.request('release.download', {
			'data': {
				'id': release.id
			}
		});
	},

	ignore: function(release){
		var self = this;

		Api.request('release.ignore', {
			'data': {
				'id': release.id
			}
		})

	}

});