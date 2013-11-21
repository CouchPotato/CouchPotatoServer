var UtorrentBase = new Class({

	setup: function(data){
		var self = this;

		self.dirs = ["dir1","dir2"];

		App.addEvent('load', self.addSettings.bind(self))

	},

	addSettings: function(){
		var self = this;

		self.api_request = Api.request('utorrent.get_downloads_directories', {
			'onComplete': self.fill(self)
		});

		self.settings = App.getPage('Settings')
		self.settings.addEvent('create', function(){
			var tab = self.settings.createSubTab('utorrent', {
				'label': 'uTorrent',
				'name': 'utorrent',
				'subtab_label': 'uTorrents'
			}, self.settings.tabs.searcher ,'searcher');

			self.tab = tab.tab;
			self.content = tab.content;

			//self.createProfiles();

		})

	},

	fill: function(json){

		var self = this;

		if(!json || json.count == 0){
			window.alert("error");
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
