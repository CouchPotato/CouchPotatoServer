var NotificationBase = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		// Listener
		App.addEvent('load', self.request.bind(self));
		self.addEvent('notification', self.notify.bind(self))
		
		// Add test buttons to settings page
		App.addEvent('load', self.addTestButtons.bind(self));

	},

	request: function(){
		var self = this;

		Api.request('core_notifier.listener', {
			'initialDelay': 100,
    		'delay': 3000,
    		'onComplete': self.processData.bind(self)
		}).startTimer()

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
		
		var name = fieldset.getElement('h2').get('text');
		
		new Element('.ctrlHolder.test_button').adopt(
			new Element('a.button', {
				'text': 'Test '+name,
				'events': {
					'click': function(){
						Api.request('notify.'+plugin_name+'.test', {
							'onComplete': function(json){
								alert(json.success)
							}
						});
					}
				}
			})
		).inject(fieldset);
	}

});

window.Notification = new NotificationBase();
