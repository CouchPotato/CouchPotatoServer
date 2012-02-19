var NotificationBase = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		// Listener
		App.addEvent('load', self.startInterval.bind(self));
		App.addEvent('unload', self.stopTimer.bind(self));
		self.addEvent('notification', self.notify.bind(self))

		// Add test buttons to settings page
		App.addEvent('load', self.addTestButtons.bind(self));

	},

	startInterval: function(){
		var self = this;

		self.request = Api.request('core_notifier.listener', {
			'initialDelay': 100,
    		'delay': 3000,
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

	notify: function(data){
		var self = this;

	},

	processData: function(json){
		var self = this;

		Array.each(json.result, function(result){
			App.fireEvent(result.type, result.data)
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
