var Movie = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],

	actions: null,
	details: null,

	initialize: function(list, options, data){
		var self = this;

		self.actions = [];
		self.data = data;
		self.list = list;

		self.buttons = [];

		self.el = new Element('a.movie').grab(
			self.inner = new Element('div.inner')
		);
		self.el.store('klass', self);

		self.profile = Quality.getProfile(data.profile_id) || {};
		self.category = CategoryList.getCategory(data.category_id) || {};
		self.parent(self, options);

		self.addEvents();

		//if(data.identifiers.imdb == 'tt3181822'){
		//	self.el.fireEvent('mouseenter');
		//	self.openDetails();
		//}
	},

	openDetails: function(){
		var self = this;

		if(!self.details){
			self.details = new MovieDetails(self, {
				'level': 3
			});

			// Add action items
			self.actions.each(function(action, nr){
				var details = action.getDetails();
				if(details){
					self.details.addSection(action.getLabel(), details);
				}
				else {
					var button = action.getDetailButton();
					if(button){
						self.details.addButton(button);
					}
				}
			});
		}

		App.getPageContainer().grab(self.details);

		requestTimeout(self.details.open.bind(self.details), 20);
	},

	addEvents: function(){
		var self = this;

		self.global_events = {};

		// Do refresh with new data
		self.global_events['movie.update'] = function(notification){
			if(self.data._id != notification.data._id) return;

			self.busy(false);
			requestTimeout(function(){
				self.update(notification);
			}, 2000);
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
				self.busy(false);
		};
		App.on('movie.searcher.ended', self.global_events['movie.searcher.ended']);

		// Reload when releases have updated
		self.global_events['release.update_status'] = function(notification){
			var data = notification.data;
			if(data && self.data._id == data.media_id){

				if(!self.data.releases)
					self.data.releases = [];

				var updated = false;
				self.data.releases.each(function(release){
					if(release._id == data._id){
						release.status = data.status;
						updated = true;
					}
				});

				if(updated)
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

		if(self.details)
			self.details.close();

		// Remove events
		Object.each(self.global_events, function(handle, listener){
			App.off(listener, handle);
		});
	},

	busy: function(set_busy, timeout){
		var self = this;

		if(!set_busy){
			requestTimeout(function(){
				if(self.spinner){
					self.mask.fade('out');
					requestTimeout(function(){
						if(self.mask)
							self.mask.destroy();
						if(self.spinner)
							self.spinner.destroy();
						self.spinner = null;
						self.mask = null;
					}, timeout || 400);
				}
			}, timeout || 1000);
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

		self.actions = [];
		self.data = notification.data;
		self.inner.empty();

		self.profile = Quality.getProfile(self.data.profile_id) || {};
		self.category = CategoryList.getCategory(self.data.category_id) || {};
		self.create();

		self.select(self.select_checkbox.get('checked'));

		self.busy(false);
	},

	create: function(){
		var self = this;

		self.el.addClass('status_'+self.get('status'));

		var eta_date = self.getETA();

		var rating, stars;
		if(['suggested','chart'].indexOf(self.data.status) > -1 && self.data.info && self.data.info.rating && self.data.info.rating.imdb){
			rating = Array.prototype.slice.call(self.data.info.rating.imdb);

			stars = [];

			var half_rating = rating[0]/2;
			for(var i = 1; i <= 5; i++){
				if(half_rating >= 1)
					stars.push(new Element('span.icon-star'));
				else if(half_rating > 0)
					stars.push(new Element('span.icon-star-half'));
				else
					stars.push(new Element('span.icon-star-empty'));

				half_rating -= 1;
			}
		}

		var thumbnail = new Element('div.poster');

		if(self.data.files && self.data.files.image_poster && self.data.files.image_poster.length > 0){
			thumbnail = new Element('div', {
				'class': 'type_image poster',
				'styles': {
					'background-image': 'url(' + Api.createUrl('file.cache') + self.data.files.image_poster[0].split(Api.getOption('path_sep')).pop() +')'
				}
			});
		}
		else if(self.data.info && self.data.info.images && self.data.info.images.poster && self.data.info.images.poster.length > 0){
			thumbnail = new Element('div', {
				'class': 'type_image poster',
				'styles': {
					'background-image': 'url(' + self.data.info.images.poster[0] +')'
				}
			});
		}

		self.inner.adopt(
			self.select_checkbox = new Element('input[type=checkbox]'),
			new Element('div.poster_container').adopt(
				thumbnail,
				self.actions_el = new Element('div.actions')
			),
			new Element('div.info').adopt(
				new Element('div.title').adopt(
					new Element('span', {
						'text': self.getTitle() || 'n/a'
					}),
					new Element('div.year', {
						'text': self.data.info.year || 'n/a'
					})
				),
				eta_date ? new Element('div.eta', {
					'text': eta_date,
					'title': 'ETA'
				}) : null,
				self.quality = new Element('div.quality'),
				rating ? new Element('div.rating[title='+rating[0]+']').adopt(
					stars,
					new Element('span.votes[text=('+rating.join(' / ')+')][title=Votes]')
				) : null
			)
		);

		if(!thumbnail)
			self.el.addClass('no_thumbnail');

		// Add profile
		if(self.profile.data)
			self.profile.getTypes().each(function(type){

				var q = self.addQuality(type.get('quality'), type.get('3d'));
				if((type.finish === true || type.get('finish')) && !q.hasClass('finish')){
					q.addClass('finish');
					q.set('title', q.get('title') + ' Will finish searching for this movie if this quality is found.');
				}

			});

		// Add releases
		self.updateReleases();

	},


	onClick: function(e){
		var self = this;

		if(e.target.getParents('.actions').length === 0 && e.target != self.select_checkbox){
			(e).stopPropagation();
			self.addActions();
			self.openDetails();
		}
	},

	addActions: function(){
		var self = this;

		if(self.actions.length <= 0){
			self.options.actions.each(function(a){
				var action = new a(self),
					button = action.getButton();
				if(button){
					self.actions_el.grab(button);
					self.buttons.push(button);
				}

				self.actions.push(action);
			});
		}
	},

	onMouseenter: function(){
		var self = this;

		if(App.mobile_screen) return;
		self.addActions();

		if(self.list.current_view == 'thumb'){
			self.el.addClass('hover_start');
			requestTimeout(function(){
				self.el.removeClass('hover_start');
			}, 300);

			dynamics.css(self.inner, {
				scale: 1
			});

			dynamics.animate(self.inner, {
				scale: 0.9
			}, { type: dynamics.bounce });

			self.buttons.each(function(el, nr){

				dynamics.css(el, {
					opacity: 0,
					translateY: 50
				});

				dynamics.animate(el, {
					opacity: 1,
					translateY: 0
				}, {
					type: dynamics.spring,
					frequency: 200,
					friction: 300,
					duration: 800,
					delay: 100 + (nr * 40)
				});

			});
		}
	},

	updateReleases: function(){
		var self = this;
		if(!self.data.releases || self.data.releases.length === 0) return;

		self.data.releases.each(function(release){

			var q = self.quality.getElement('.q_'+ release.quality+(release.is_3d ? '.is_3d' : ':not(.is_3d)')),
				status = release.status;

			if(!q && (status == 'snatched' || status == 'seeding' || status == 'done'))
				q = self.addQuality(release.quality, release.is_3d || false);

			if (q && !q.hasClass(status)){
				q.addClass(status);
				q.set('title', (q.get('title') ? q.get('title') : '') + ' status: '+ status);
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

	getTitle: function(prefixed){
		var self = this;

		if(self.data.title)
			return prefixed ? self.data.title : self.getUnprefixedTitle(self.data.title);
		else if(self.data.info && self.data.info.titles && self.data.info.titles.length > 0)
			return prefixed ? self.data.info.titles[0] : self.getUnprefixedTitle(self.data.info.titles[0]);

		return 'Unknown movie';
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

	getIdentifier: function(){
		var self = this;

		try {
			return self.get('identifiers').imdb;
		}
		catch (e){ }

		return self.get('imdb');
	},

	getETA: function(format){
		var self = this,
			d = new Date(),
			now = Math.round(+d/1000),
			eta = null,
			eta_date = '';

		if(self.data.info.release_date)
			[self.data.info.release_date.dvd, self.data.info.release_date.theater].each(function(timestamp){
				if (timestamp > 0 && (eta === null || Math.abs(timestamp - now) < Math.abs(eta - now)))
					eta = timestamp;
			});

		if(eta){
			eta_date = new Date(eta * 1000);
			if(+eta_date/1000 < now){
				eta_date = null;
			}
			else {
				eta_date = format ? eta_date.format(format) : (eta_date.format('%b') + (d.getFullYear() != eta_date.getFullYear() ? ' ' + eta_date.getFullYear() : ''));
			}
		}

		return (now+8035200 > eta) ? eta_date : '';
	},

	get: function(attr){
		return this.data[attr] || this.data.info[attr];
	},

	select: function(select){
		var self = this;
		self.select_checkbox.set('checked', select);
		self.el[self.select_checkbox.get('checked') ? 'addClass' : 'removeClass']('checked');
	},

	isSelected: function(){
		return this.select_checkbox.get('checked');
	},

	toElement: function(){
		return this.el;
	}

});
