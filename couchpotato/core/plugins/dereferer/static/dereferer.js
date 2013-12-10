var DerefererBase = new Class({

	Implements: [Events],

	initialize: function () {
		var self = this;

		App.on('dereferer.update_config', self.setConfig.bind(self));
	},

	getConfigFromApi: function () {
		var self = this;

		Api.request('dereferer.settings', {
			'onComplete': function (json) {
				self.config = json;
			}
		});
	},

	setConfig: function (notification) {
		var self = this;

		self.config = notification.data;
	},


	getURL: function (target) {
		var url = target;
		var self = this;

		if (self.config.enabled) {
			url = self.config.service_url + target;
		}

		return url;
	},

	getInfo: function () {
		var self = this;

		return self.config;
	}
});

var Dereferer = new DerefererBase();

window.addEvent('load', function () {
	Dereferer.getConfigFromApi();
});
