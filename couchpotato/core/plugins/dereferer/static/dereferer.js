var DerefererBase = new Class({

	Implements: [Events],

	initialize: function(){
		var self = this;

		App.addEvent('load', self.info.bind(self, 2000))
		App.addEvent('unload', function(){
			if(self.timer)
				clearTimeout(self.timer);
		});
	},

	info: function(timeout){
		var self = this;

		if(self.timer) clearTimeout(self.timer);

		self.timer = setTimeout(function(){
			Api.request('dereferer.info', {
				'onComplete': function(json){
					self.json = json;
					self.fireEvent('loaded', [json]);
				}
			})
		}, (timeout || 0))

	},

    getURL: function(target) {
        var url = target;
        if (this.json.enabled) {
            url = this.json.service_url + target;
        }

        return url;
    },

	getInfo: function(){
		return this.json;
	}
});

var Dereferer = new DerefererBase();


