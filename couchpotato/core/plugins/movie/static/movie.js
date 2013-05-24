var Movie = new Class({

	Extends: BlockBase,

	action: {},

	initialize: function(list, options, data){
		var self = this;

		self.data = data;
		self.view = options.view || 'details';
		self.list = list;

		self.el = new Element('div.movie');

		self.profile = Quality.getProfile(data.profile_id) || {};
		self.parent(self, options);

		self.addEvents();
	},

	addEvents: function(){
		var self = this;

		App.addEvent('movie.update.'+self.data.id, function(notification){
			self.busy(false);
			self.removeView();
			self.update.delay(2000, self, notification);
		});

		['movie.busy', 'searcher.started'].each(function(listener){
			App.addEvent(listener+'.'+self.data.id, function(notification){
				if(notification.data)
					self.busy(true)
			});
		})

		App.addEvent('searcher.ended.'+self.data.id, function(notification){
			if(notification.data)
				self.busy(false)
		});
	},

	destroy: function(){
		var self = this;

		self.el.destroy();
		delete self.list.movies_added[self.get('id')];
		self.list.movies.erase(self)

		self.list.checkIfEmpty();

		// Remove events
		App.removeEvents('movie.update.'+self.data.id);
		['movie.busy', 'searcher.started'].each(function(listener){
			App.removeEvents(listener+'.'+self.data.id);
		})
	},

	busy: function(set_busy){
		var self = this;

		if(!set_busy){
			setTimeout(function(){
				if(self.spinner){
					self.mask.fade('out');
					setTimeout(function(){
						if(self.mask)
							self.mask.destroy();
						if(self.spinner)
							self.spinner.el.destroy();
						self.spinner = null;
						self.mask = null;
					}, 400);
				}
			}, 1000)
		}
		else if(!self.spinner) {
			self.createMask();
			self.spinner = createSpinner(self.mask);
			self.mask.fade('in');
		}
	},

	createMask: function(){
		var self = this;
		self.mask = new Element('div.mask', {
			'styles': {
				'z-index': 4
			}
		}).inject(self.el, 'top').fade('hide');
	},

	positionMask: function(){
		var self = this,
			s = self.el.getSize()

		return self.mask.setStyles({
			'width': s.x,
			'height': s.y
		}).position({
			'relativeTo': self.el
		})
	},

	update: function(notification){
		var self = this;

		self.data = notification.data;
		self.el.empty();
		self.removeView();

		self.profile = Quality.getProfile(self.data.profile_id) || {};
		self.create();

		self.busy(false);
	},

	create: function(){
		var self = this;

		var s = Status.get(self.get('status_id'));
		self.el.addClass('status_'+s.identifier);

		self.el.adopt(
			self.select_checkbox = new Element('input[type=checkbox].inlay', {
				'events': {
					'change': function(){
						self.fireEvent('select')
					}
				}
			}),
			self.thumbnail = File.Select.single('poster', self.data.library.files),
			self.data_container = new Element('div.data.inlay.light').adopt(
				self.info_container = new Element('div.info').adopt(
					new Element('div.title').adopt(
						self.title = new Element('span', {
							'text': self.getTitle() || 'n/a'
						}),
						self.year = new Element('div.year', {
							'text': self.data.library.year || 'n/a'
						})
					),
					self.description = new Element('div.description', {
						'text': self.data.library.plot
					}),
					self.quality = new Element('div.quality', {
						'events': {
							'click': function(e){
								var releases = self.el.getElement('.actions .releases');
								if(releases.isVisible())
									releases.fireEvent('click', [e])
							}
						}
					})
				),
				self.actions = new Element('div.actions')
			)
		);

		if(self.thumbnail.empty)
			self.el.addClass('no_thumbnail');

		//self.changeView(self.view);
		self.select_checkbox_class = new Form.Check(self.select_checkbox);

		// Add profile
		if(self.profile.data)
			self.profile.getTypes().each(function(type){

				var q = self.addQuality(type.quality_id || type.get('quality_id'));
				if((type.finish == true || type.get('finish')) && !q.hasClass('finish')){
					q.addClass('finish');
					q.set('title', q.get('title') + ' Will finish searching for this movie if this quality is found.')
				}

			});

		// Add releases
		self.data.releases.each(function(release){

			var q = self.quality.getElement('.q_id'+ release.quality_id),
				status = Status.get(release.status_id);

			if(!q && (status.identifier == 'snatched' || status.identifier == 'done'))
				var q = self.addQuality(release.quality_id)

			if (status && q && !q.hasClass(status.identifier)){
				q.addClass(status.identifier);
				q.set('title', (q.get('title') ? q.get('title') : '') + ' status: '+ status.label)
			}

		});

		Object.each(self.options.actions, function(action, key){
			self.action[key.toLowerCase()] = action = new self.options.actions[key](self)
			if(action.el)
				self.actions.adopt(action)
		});

	},

	addQuality: function(quality_id){
		var self = this;

		var q = Quality.getQuality(quality_id);
		return new Element('span', {
			'text': q.label,
			'class': 'q_'+q.identifier + ' q_id' + q.id,
			'title': ''
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
			self.changeView('details');

			self.el.addEvent('outerClick', function(){
				self.removeView();
				self.slide('out')
			})
			el.show();
			self.data_container.addClass('hide_right');
		}
		else {
			self.el.removeEvents('outerClick')

			setTimeout(function(){
				self.el.getElements('> :not(.data):not(.poster):not(.movie_container)').hide();
			}, 600);

			self.data_container.removeClass('hide_right');
		}
	},

	changeView: function(new_view){
		var self = this;

		self.el
			.removeClass(self.view+'_view')
			.addClass(new_view+'_view')

		self.view = new_view;
	},

	removeView: function(){
		var self = this;

		self.el.removeClass(self.view+'_view')
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
	},

	toElement: function(){
		return this.el;
	}

});