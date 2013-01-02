var ApiClass = new Class({

	setup: function(options){
		var self = this

		self.options = options;
	},

	request: function(type, options){
		var self = this;

		var r_type = self.options.is_remote ? 'JSONP' : 'JSON';
		return new Request[r_type](Object.merge({
			'callbackKey': 'callback_func',
			'method': 'get',
			'url': self.createUrl(type, {'t': randomString()}),
		}, options)).send()
	},

	createUrl: function(action, params){
		return this.options.url + (action || 'default') + '/' + (params ? '?'+Object.toQueryString(params) : '')
	},

	getOption: function(name){
		return this.options[name]
	}

});
window.Api = new ApiClass()