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
		self.log = new Element('div.container.loading', {
			'text': 'loading...'
		}).inject(self.el);

		Api.request('logging.get', {
			'data': {
				'nr': nr
			},
			'onComplete': function(json){
				self.log.set('html', '<pre>'+json.log+'</pre>');
				self.log.removeClass('loading');

				var nav = new Element('ul.nav').inject(self.log, 'top');
				for (var i = 0; i < json.total; i++) {
					new Element('li', {
						'text': i+1,
						'class': nr == i ? 'active': '',
						'events': {
							'click': function(e){
								self.getLogs(e.target.get('text')-1);
							}
						}
					}).inject(nav);
				};
			}
		});

	}

})