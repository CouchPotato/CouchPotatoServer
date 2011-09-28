Page.Log = new Class({

	Extends: PageBase,

	name: 'log',
	title: 'Show recent logs.',

	indexAction: function(){
		var self = this;

		self.getLogs(0);

	},

	getLogs: function(nr){
		var self = this;

		if(self.log) self.log.destroy();
		self.log = new Element('div.log', {
			'text': 'loading...'
		}).inject(self.el);

		Api.request('logging.get', {
			'data': {
				'nr': nr
			},
			'onComplete': function(json){
				self.log.set('html', '<pre>'+json.log+'</pre>')

				var nav = new Element('ul.nav').inject(self.log, 'top');
				for (var i = 0; i < json.total; i++) {
					p(i, json.total);
					new Element('li', {
						'text': i+1,
						'events': {
							'click': function(){  self.getLogs(i); }
						}
					}).inject(nav)
				};
			}
		});

	}

})