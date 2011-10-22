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

		self.message = new Element('div.message.update').adopt(
			new Element('span', {
				'text': 'A new version is available'
			}),
			new Element('a', {
				'href': 'https://github.com/'+data.repo_name+'/compare/'+data.version.hash+'...'+data.update_version.hash,
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
					App.restart();

					$(document.body).set('spin', {
						'message': 'Updating'
					});
					$(document.body).spin();

					var checks = 0;
					var interval = 0;
					interval = setInterval(function(){
						Api.request('', {
							'onSuccess': function(){
								if(checks > 2){
									clearInterval(interval);
									$(document.body).unspin();
									self.info();
								}
							}
						});
						checks++;
					}, 500)

				}

			}
		});
	}

});

var Updater = new UpdaterBase();
