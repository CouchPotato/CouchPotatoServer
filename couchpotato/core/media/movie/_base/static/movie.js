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
		self.category = CategoryList.getCategory(data.category_id) || {};
		self.parent(self, options);

		self.addEvents();
	},

	addEvents: function(){
		var self = this;

		self.global_events = {};

		// Do refresh with new data
		self.global_events['movie.update'] = function(notification){
			if(self.data._id != notification.data._id) return;

			self.busy(false);
			self.removeView();
			self.update.delay(2000, self, notification);
		};
		App.on('movie.update', self.global_events['movie.update']);

		// Add spinner on load / search
		['media.busy', 'movie.searcher.started'].each(function(listener){
			self.global_events[listener] = function(notification){
				if(notification.data && (self.data._id == notification.data._id || (typeOf(notification.data._id) == 'array' && notification.data._id.indexOf(self.data._id) > -1)))
					self.busy(true);
			};
			App.on(listener, self.global_events[listener]);
		});

		// Remove spinner
		self.global_events['movie.searcher.ended'] = function(notification){
			if(notification.data && self.data._id == notification.data._id)
				self.busy(false)
		};
		App.on('movie.searcher.ended', self.global_events['movie.searcher.ended']);

		// Reload when releases have updated
		self.global_events['release.update_status'] = function(notification){
			var data = notification.data;
			if(data && self.data._id == data.movie_id){

				if(!self.data.releases)
					self.data.releases = [];

				self.data.releases.push({'quality': data.quality, 'status': data.status});
				self.updateReleases();
			}
		};

		App.on('release.update_status', self.global_events['release.update_status']);

	},

	destroy: function(){
		var self = this;

		self.el.destroy();
		delete self.list.movies_added[self.get('id')];
		self.list.movies.erase(self);

		self.list.checkIfEmpty();

		// Remove events
		Object.each(self.global_events, function(handle, listener){
			App.off(listener, handle);
		});
	},

	busy: function(set_busy, timeout){
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
					}, timeout || 400);
				}
			}, timeout || 1000)
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

	update: function(notification){
		var self = this;

		self.data = notification.data;
		self.el.empty();
		self.removeView();

		self.profile = Quality.getProfile(self.data.profile_id) || {};
		self.category = CategoryList.getCategory(self.data.category_id) || {};
		self.create();

		self.busy(false);
	},

	create: function(){
		var self = this;

		self.el.addClass('status_'+self.get('status'));

		self.el.adopt(
			self.select_checkbox = new Element('input[type=checkbox].inlay', {
				'events': {
					'change': function(){
						self.fireEvent('select')
					}
				}
			}),
			self.thumbnail = (self.data.files && self.data.files.image_poster) ? new Element('img', {
				'class': 'type_image poster',
				'src': Api.createUrl('file.cache') + self.data.files.image_poster[0].split(Api.getOption('path_sep')).pop()
			}): null,
			self.data_container = new Element('div.data.inlay.light').adopt(
				self.info_container = new Element('div.info').adopt(
					new Element('div.title').adopt(
						self.title = new Element('span', {
							'text': self.getTitle() || 'n/a'
						}),
						self.year = new Element('div.year', {
							'text': self.data.info.year || 'n/a'
						})
					),
					self.description = new Element('div.description', {
						'text': self.data.info.plot
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

		if(!self.thumbnail)
			self.el.addClass('no_thumbnail');

		//self.changeView(self.view);
		self.select_checkbox_class = new Form.Check(self.select_checkbox);

		// Add profile
		if(self.profile.data)
			self.profile.getTypes().each(function(type){

				var q = self.addQuality(type.get('quality'), type.get('3d'));
				if((type.finish == true || type.get('finish')) && !q.hasClass('finish')){
					q.addClass('finish');
					q.set('title', q.get('title') + ' Will finish searching for this movie if this quality is found.')
				}

			});

		// Add releases
		self.updateReleases();

		Object.each(self.options.actions, function(action, key){
			self.action[key.toLowerCase()] = action = new self.options.actions[key](self);
			if(action.el)
				self.actions.adopt(action)
		});

	},

	updateReleases: function(){
		var self = this;
		if(!self.data.releases || self.data.releases.length == 0) return;

		self.data.releases.each(function(release){

			var q = self.quality.getElement('.q_'+ release.quality+(release.is_3d ? '.is_3d' : ':not(.is_3d)')),
				status = release.status;

			if(!q && (status == 'snatched' || status == 'seeding' || status == 'done'))
				q = self.addQuality(release.quality, release.is_3d || false);

			if (q && !q.hasClass(status)){
				q.addClass(status);
				q.set('title', (q.get('title') ? q.get('title') : '') + ' status: '+ status)
			}

		});
	},

	addQuality: function(quality, is_3d){
		var self = this;

		var q = Quality.getQuality(quality);
		return new Element('span', {
			'text': q.label + (is_3d ? ' 3D' : ''),
			'class': 'q_'+q.identifier + (is_3d ? ' is_3d' : ''),
			'title': ''
		}).inject(self.quality);

	},

	getTitle: function(){
		var self = this;

		if(self.data.title)
			return self.getUnprefixedTitle(self.data.title);
		else if(self.data.info.titles.length > 0)
			return self.getUnprefixedTitle(self.data.info.titles[0]);

		return 'Unknown movie'
	},

	getUnprefixedTitle: function(t){
		if(t.substr(0, 4).toLowerCase() == 'the ')
			t = t.substr(4) + ', The';
		else if(t.substr(0, 3).toLowerCase() == 'an ')
			t = t.substr(3) + ', An';
		else if(t.substr(0, 2).toLowerCase() == 'a ')
			t = t.substr(2) + ', A';
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
			});
			el.show();
			self.data_container.addClass('hide_right');
		}
		else {
			self.el.removeEvents('outerClick');

			setTimeout(function(){
				if(self.el)
					self.el.getElements('> :not(.data):not(.poster):not(.movie_container)').hide();
			}, 600);

			self.data_container.removeClass('hide_right');
		}
	},

	changeView: function(new_view){
		var self = this;

		if(self.el)
			self.el
				.removeClass(self.view+'_view')
				.addClass(new_view+'_view');

		self.view = new_view;
	},

	removeView: function(){
		var self = this;

		self.el.removeClass(self.view+'_view')
	},

	getIdentifier: function(){
		var self = this;

		try {
			return self.get('identifiers').imdb;
		}
		catch (e){ }

		return self.get('imdb');
	},

	get: function(attr){
		return this.data[attr] || this.data.info[attr]
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
