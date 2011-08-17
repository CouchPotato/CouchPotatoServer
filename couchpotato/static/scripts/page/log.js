Page.Log = new Class({

	Extends: PageBase,

	name: 'log',
	title: 'Show recent logs.',
	
	indexAction: function(){
		var self = this;
		
		if(self.log) self.log.destroy();
		self.log = new Element('div.log', {
			'text': 'loading...'
		}).inject(self.el)
		
		Api.request('logging.get', {
			'data': {
				'nr': 0
			},
			'onComplete': function(json){
				self.log.set('html', '<pre>'+json.log+'</pre>')
			}
		})
		
	}

})