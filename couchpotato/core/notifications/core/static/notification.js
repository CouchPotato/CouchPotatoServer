var NotificationBase = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		// Listener
		App.addEvent('load', self.startInterval.bind(self));
		App.addEvent('unload', self.stopTimer.bind(self));
		App.addEvent('notification', self.notify.bind(self));

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
		})

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
				'data': {
					'ids': ids.join(',')
				},
				'onSuccess': function(){
					self.setBadge('')
				}
			})

	},

	startInterval: function(){
		var self = this;

		self.request = Api.request('notification.listener', {
			'initialDelay': 100,
    		'delay': 3000,
    		'data': {'init':true},
    		'onSuccess': self.processData.bind(self)
		})

		self.request.startTimer()

	},

	startTimer: function(){
		if(this.request)
			this.request.startTimer()
	},

	stopTimer: function(){
		if(this.request)
			this.request.stopTimer()
	},

	processData: function(json){
		var self = this;

		self.request.options.data = {}
		Array.each(json.result, function(result){
			App.fireEvent(result.type, result)
		})
	},

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
