var NotificationBase = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		// Listener
		App.addEvent('unload', self.stopPoll.bind(self));
		App.addEvent('reload', self.startInterval.bind(self, [true]));
		App.addEvent('notification', self.notify.bind(self));
		App.addEvent('message', self.showMessage.bind(self));

		// Add test buttons to settings page
		App.addEvent('load', self.addTestButtons.bind(self));

		// Notification bar
		self.notifications = []
		App.addEvent('load', function(){

			App.block.notification = new Block.Menu(self, {
				'class': 'notification_menu',
				'onOpen': self.markAsRead.bind(self)
			})
			$(App.block.notification).inject(App.getBlock('search'), 'after');
			self.badge = new Element('div.badge').inject(App.block.notification, 'top').hide();

			/* App.getBlock('notification').addLink(new Element('a.more', {
				'href': App.createUrl('notifications'),
				'text': 'Show older notifications'
			})); */
		});

		window.addEvent('load', function(){
			self.startInterval.delay(Browser.safari ? 100 : 0, self)
		});

	},

	notify: function(result){
		var self = this;

		var added = new Date();
			added.setTime(result.added*1000)

		result.el = App.getBlock('notification').addLink(
			new Element('span.'+(result.read ? 'read' : '' )).adopt(
				new Element('span.message', {'text': result.message}),
				new Element('span.added', {'text': added.timeDiffInWords(), 'title': added})
			)
		, 'top');
		self.notifications.include(result);

		if(!result.read)
			self.setBadge(self.notifications.filter(function(n){ return !n.read}).length)

	},

	setBadge: function(value){
		var self = this;
		self.badge.set('text', value)
		self.badge[value ? 'show' : 'hide']()
	},

	markAsRead: function(){
		var self = this;

		var rn = self.notifications.filter(function(n){
			return !n.read
		})

		var ids = []
		rn.each(function(n){
			ids.include(n.id)
		})

		if(ids.length > 0)
			Api.request('notification.markread', {
				'onSuccess': function(){
					self.setBadge('')
				}
			})

	},

	startInterval: function(force){
		var self = this;

		if(self.stopped && !force){
			self.stopped = false;
			return;
		}

		Api.request('notification.listener', {
    		'data': {'init':true},
    		'onSuccess': self.processData.bind(self)
		}).send()

	},

	startPoll: function(){
		var self = this;

		if(self.stopped || (self.request && self.request.isRunning()))
			return;

		self.request = Api.request('nonblock/notification.listener', {
    		'onSuccess': self.processData.bind(self),
    		'data': {
    			'last_id': self.last_id
    		},
    		'onFailure': function(){
    			self.startPoll.delay(2000, self)
    		}
		}).send()

	},

	stopPoll: function(){
		if(this.request)
			this.request.cancel()
		this.stopped = true;
	},

	processData: function(json){
		var self = this;

		// Process data
		if(json){
			Array.each(json.result, function(result){
				App.fireEvent(result.type, result);
				if(result.message && result.read === undefined)
					self.showMessage(result.message);
			})

			if(json.result.length > 0)
				self.last_id = json.result.getLast().message_id
		}

		// Restart poll
		self.startPoll()
	},

	showMessage: function(message){
		var self = this;

		if(!self.message_container)
			self.message_container = new Element('div.messages').inject(document.body);

		var new_message = new Element('div.message', {
			'text': message
		}).inject(self.message_container);

		setTimeout(function(){
			new_message.addClass('show')
		}, 10);

		setTimeout(function(){
			new_message.addClass('hide')
			setTimeout(function(){
				new_message.destroy();
			}, 1000);
		}, 4000);

	},

	// Notification setting tests
	addTestButtons: function(){
		var self = this;

		var setting_page = App.getPage('Settings')
		setting_page.addEvent('create', function(){
			Object.each(setting_page.tabs.notifications.groups, self.addTestButton.bind(self))
		})

	},

	addTestButton: function(fieldset, plugin_name){
		var self = this;

		new Element('.ctrlHolder.test_button').adopt(
			new Element('a.button', {
				'text': self.testButtonName(fieldset),
				'events': {
					'click': function(){
						var button = fieldset.getElement('.test_button .button');
							button.set('text', 'Sending notification');

						Api.request('notify.'+plugin_name+'.test', {
							'onComplete': function(json){

								button.set('text', self.testButtonName(fieldset));

								if(json.success){
									var message = new Element('span.success', {
										'text': 'Notification successful'
									}).inject(button, 'after')
								}
								else {
									var message = new Element('span.failed', {
										'text': 'Notification failed. Check logs for details.'
									}).inject(button, 'after')
								}

								(function(){
									message.destroy();
								}).delay(3000)
							}
						});
					}
				}
			})
		).inject(fieldset);
	},

	testButtonName: function(fieldset){
		var name = fieldset.getElement('h2').get('text');
		return 'Test '+name;
	}

});

window.Notification = new NotificationBase();
