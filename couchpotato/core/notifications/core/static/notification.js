var NotificationBase = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],
	stopped: false,

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		// Listener
		App.addEvent('unload', self.stopPoll.bind(self));
		App.addEvent('reload', self.startInterval.bind(self, [true]));
		App.on('notification', self.notify.bind(self));
		App.on('message', self.showMessage.bind(self));

		// Add test buttons to settings page
		App.addEvent('loadSettings', self.addTestButtons.bind(self));

		// Notification bar
		self.notifications = [];
		App.addEvent('load', function(){

			App.block.notification = new BlockMenu(self, {
				'button_class': 'icon-notifications',
				'class': 'notification_menu',
				'onOpen': self.markAsRead.bind(self)
			});
			$(App.block.notification).inject(App.getBlock('search'), 'after');
			self.badge = new Element('div.badge').inject(App.block.notification, 'top').hide();

			requestTimeout(function(){
				self.startInterval();
			}, $(window).getSize().x <= 480 ? 2000 : 100);

		});
	},

	notify: function(result){
		var self = this;

		var added = new Date();
			added.setTime(result.added*1000);

		result.el = App.getBlock('notification').addLink(
			new Element('span.'+(result.read ? 'read' : '' )).adopt(
				new Element('span.message', {'html': result.message}),
				new Element('span.added', {'text': added.timeDiffInWords(), 'title': added})
			), 'top');
		self.notifications.include(result);

		if((result.important !== undefined || result.sticky !== undefined) && !result.read){
			var sticky = true;
			App.trigger('message', [result.message, sticky, result]);
		}
		else if(!result.read){
			self.setBadge(self.notifications.filter(function(n){ return !n.read; }).length);
		}

	},

	setBadge: function(value){
		var self = this;
		self.badge.set('text', value);
		self.badge[value ? 'show' : 'hide']();
	},

	markAsRead: function(force_ids){
		var self = this,
			ids = force_ids;

		if(!force_ids) {
			var rn = self.notifications.filter(function(n){
				return !n.read && n.important === undefined;
			});

			ids = [];
			rn.each(function(n){
				ids.include(n._id);
			});
		}

		if(ids.length > 0)
			Api.request('notification.markread', {
				'data': {
					'ids': ids.join(',')
				},
				'onSuccess': function(){
					self.setBadge('');
				}
			});

	},

	startInterval: function(force){
		var self = this;

		if(self.stopped && !force){
			self.stopped = false;
			return;
		}

		self.request = Api.request('notification.listener', {
			'data': {'init':true},
			'onSuccess': function(json){
				self.processData(json, true);
			}
		}).send();

		requestInterval(function(){

			if(self.request && self.request.isRunning()){
				self.request.cancel();
				self.startPoll();
			}

		}, 120000);

	},

	startPoll: function(){
		var self = this;

		if(self.stopped)
			return;

		if(self.request && self.request.isRunning())
			self.request.cancel();

		self.request = Api.request('nonblock/notification.listener', {
			'onSuccess': function(json){
				self.processData(json, false);
			},
			'data': {
				'last_id': self.last_id
			},
			'onFailure': function(){
				requestTimeout(self.startPoll.bind(self), 2000);
			}
		}).send();

	},

	stopPoll: function(){
		if(this.request)
			this.request.cancel();
		this.stopped = true;
	},

	processData: function(json, init){
		var self = this;

		// Process data
		if(json && json.result){
			Array.each(json.result, function(result){
				App.trigger(result._t || result.type, [result]);
				if(result.message && result.read === undefined && !init)
					self.showMessage(result.message);
			});

			if(json.result.length > 0)
				self.last_id = json.result.getLast().message_id;
		}

		// Restart poll
		requestTimeout(self.startPoll.bind(self), 1500);
	},

	showMessage: function(message, sticky, data){
		var self = this;

		if(!self.message_container)
			self.message_container = new Element('div.messages').inject(document.body);

		var new_message = new Element('div', {
			'class': 'message' + (sticky ? ' sticky' : ''),
			'html': '<div class="inner">' + message + '</div>'
		}).inject(self.message_container, 'top');

		requestTimeout(function(){
			new_message.addClass('show');
		}, 10);

		var hide_message = function(){
			new_message.addClass('hide');
			requestTimeout(function(){
				new_message.destroy();
			}, 1000);
		};

		if(sticky)
			new_message.grab(
				new Element('a.icon-cancel', {
					'events': {
						'click': function(){
							self.markAsRead([data._id]);
							hide_message();
						}
					}
				})
			);
		else
			requestTimeout(hide_message, 4000);

	},

	// Notification setting tests
	addTestButtons: function(){
		var self = this;

		var setting_page = App.getPage('Settings');
		setting_page.addEvent('create', function(){
			Object.each(setting_page.tabs.notifications.groups, self.addTestButton.bind(self));
		});

	},

	addTestButton: function(fieldset, plugin_name){
		var self = this,
			button_name = self.testButtonName(fieldset);

		if(button_name.contains('Notifications')) return;

		new Element('.ctrlHolder.test_button').grab(
			new Element('a.button', {
				'text': button_name,
				'events': {
					'click': function(){
						var button = fieldset.getElement('.test_button .button');
							button.set('text', 'Sending notification');

						Api.request('notify.'+plugin_name+'.test', {
							'onComplete': function(json){

								button.set('text', button_name);

								var message;
								if(json.success){
									message = new Element('span.success', {
										'text': 'Notification successful'
									}).inject(button, 'after');
								}
								else {
									message = new Element('span.failed', {
										'text': 'Notification failed. Check logs for details.'
									}).inject(button, 'after');
								}

								requestTimeout(function(){
									message.destroy();
								}, 3000);
							}
						});
					}
				}
			})
		).inject(fieldset);
	},

	testButtonName: function(fieldset){
		var name = fieldset.getElement('h2 .group_label').get('text');
		return 'Test '+name;
	}

});

window.Notification = new NotificationBase();
