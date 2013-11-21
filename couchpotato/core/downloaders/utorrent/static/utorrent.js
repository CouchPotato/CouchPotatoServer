var UtorrentBase = new Class({

	initialize: function(){
		var self = this;
		self.api_request = Api.request('utorrent.get_downloads_directories', {
			'onComplete': self.fill.bind(self)
		});
	},



	fill: function(json){

		var self = this;

		if(!json || json.count == 0){
			self.el.hide();
		}
		else {

			Object.each(json.directories, function(dir){
			    window.alert(dir);
			});

		}

		//self.fireEvent('loaded');

	},



})

window.Utorrent = new UtorrentBase();
