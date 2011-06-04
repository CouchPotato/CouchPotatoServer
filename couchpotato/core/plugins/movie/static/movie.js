var Movie = new Class({

	Extends: BlockBase,
	
	action: {},

	initialize: function(self, options, data){
		var self = this;

		self.data = data;

		self.profile = Quality.getProfile(data.profile_id);
		self.parent(self, options);
		self.addEvent('injected', self.afterInject.bind(self))
	},

	create: function(){
		var self = this;

		self.el = new Element('div.movie.inlay').adopt(
			self.data_container = new Element('div.data.inlay.light', {
				'tween': {
					duration: 400,
					transition: 'quint:in:out'
				}
			}).adopt(
				self.thumbnail = File.Select.single('poster', self.data.library.files),
				self.info_container = new Element('div.info').adopt(
					self.title = new Element('div.title', {
						'text': self.getTitle()
					}),
					self.year = new Element('div.year', {
						'text': self.data.library.year || 'Unknown'
					}),
					self.rating = new Element('div.rating', {
						'text': self.data.library.rating
					}),
					self.description = new Element('div.description', {
						'text': self.data.library.plot
					}),
					self.quality = new Element('div.quality', {
						'html': self.profile ? '<strong>Quality:</strong> ' + self.profile.get('label') : ''
					})
				),
				self.actions = new Element('div.actions')
			)
		);

		Object.each(self.options.actions, function(action, key){
			self.actions.adopt(
				self.action[key.toLowerCase()] = new self.options.actions[key](self)
			)
		});

		if(!self.data.library.rating)
			self.rating.hide();

	},

	afterInject: function(){
		var self = this;

		var height = self.getHeight();
		self.el.setStyle('height', height);
	},

	getTitle: function(){
		var self = this;

		var titles = self.data.library.titles;

		var title = titles.filter(function(title){
			return title['default']
		}).pop()

		if(title)
			return  title.title
		else if(titles.length > 0)
			return titles[0].title

		return 'Unknown movie'
	},

	slide: function(direction){
		var self = this;

		if(direction == 'in'){
			self.el.addEvent('outerClick', self.slide.bind(self, 'out'))
			self.data_container.tween('left', 0, self.getWidth());
		}
		else {
			self.el.removeEvents('outerClick')
			self.data_container.tween('left', self.getWidth(), 0);
		}
	},

	getHeight: function(){
		var self = this;

		if(!self.height)
			self.height = self.data_container.getCoordinates().height;

		return self.height;
	},

	getWidth: function(){
		var self = this;

		if(!self.width)
			self.width = self.data_container.getCoordinates().width;

		return self.width;
	},

	get: function(attr){
		return this.data[attr] || this.data.library[attr]
	}

});

var MovieAction = new Class({

	class_name: 'action',

	initialize: function(movie){
		var self = this;
		self.movie = movie;

		self.create();
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
		return this.el
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
		(e).stop();

		window.open('http://www.imdb.com/title/'+self.id+'/');
	}

})