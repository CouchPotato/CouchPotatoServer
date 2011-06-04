var NotificationBase = new Class({

	Extends: BlockBase,
	Implements: [Options, Events],

	initialize: function(options){
		var self = this;
		self.setOptions(options);

		App.addEvent('load', self.request.bind(self));

		self.addEvent('notification', self.notify.bind(self))

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
	}

});

window.Notification = new NotificationBase();
