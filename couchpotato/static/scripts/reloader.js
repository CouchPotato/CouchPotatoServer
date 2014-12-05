var ReloaderBase = new Class({

	initialize: function(){
		var self = this;

		App.on('watcher.changed', self.reloadFile.bind(self));

	},

	reloadFile: function(data){
		var self = this,
			urls = data.data;

		urls.each(function(url){
			var without_timestamp = url.split('?')[0],
				old_links = document.getElement('[data-url^=\''+without_timestamp+'\']');

			old_links.set('href', old_links.get('href') + 1);
		});
	}

});

var Reloader = new ReloaderBase();
