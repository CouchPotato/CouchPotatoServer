var UpdaterBase = new Class({

	Implements: [Events],

	initialize: function(){
		var self = this;

		App.addEvent('load', self.info.bind(self, 1000))
		App.addEvent('unload', function(){
			if(self.timer)
				clearTimeout(self.timer);
		});
	},

	check: function(onComplete){
		var self = this;

		Api.request('updater.check', {
			'onComplete': function(json){
				if(onComplete)
					onComplete(json);

				if(json.update_available)
					self.doUpdate();
				else {
					App.unBlockPage();
					App.fireEvent('message', 'No updates available');
				}
			}
		})

	},

	info: function(timeout){
		var self = this;

		if(self.timer) clearTimeout(self.timer);

		self.timer = setTimeout(function(){
			Api.request('updater.info', {
				'onComplete': function(json){
					self.json = json;
					self.fireEvent('loaded', [json]);

					if(json.update_version){
						self.createMessage(json);
					}
					else {
						if(self.message)
							self.message.destroy();
					}
				}
			})
		}, (timeout || 0))

	},

	getInfo: function(){
		return this.json;
	},

	createMessage: function(data){
		var self = this;

		var changelog = 'https://github.com/'+data.repo_name+'/compare/'+data.version.hash+'...'+data.branch;
		if(data.update_version.changelog)
			changelog = data.update_version.changelog + '#' + data.version.hash+'...'+data.update_version.hash

		self.message = new Element('div.message.update').adopt(
			new Element('span', {
				'text': 'A new version is available'
			}),
			new Element('a', {
				'href': changelog,
				'text': 'see what has changed',
				'target': '_blank'
			}),
			new Element('span[text=or]'),
			new Element('a', {
				'text': 'just update, gogogo!',
				'events': {
					'click': self.doUpdate.bind(self)
				}
			})
		).inject($(document.body).getElement('.header'))
	},

	doUpdate: function(){
		var self = this;

		Api.request('updater.update', {
			'onComplete': function(json){
				if(json.success){
					self.updating();
				}
			}
		});
	},

	updating: function(){
		App.blockPage('Please wait while CouchPotato is being updated with more awesome stuff.', 'Updating');
		App.checkAvailable.delay(500, App, [1000, function(){
			window.location.reload();
		}]);
		if(self.message)
			self.message.destroy();
	}

});

var Updater = new UpdaterBase();
