Block.Search = new Class({

	Extends: BlockBase,

	create: function(){
		var self = this;

		self.el = new Element('div.search_form').adopt(
			self.input = new Element('input', {
				'events': {
					'keyup': self.autocomplete.bind(self)
				}
			})
		);
	},
	
	autocomplete: function(){
		var self = this;
		
		if(self.autocomplete_timer) clearTimeout(self.autocomplete_timer)
		self.autocomplete_timer = self.list.delay(300, self)
	},
	
	list: function(){
		var self = this;
		
		if(self.api_request) self.api_request.cancel();
		self.api_request = self.api().request('movie.add.search', {
			'data': {
				'q': self.input.get('value')
			},
			'onComplete': self.fill.bind(self)
		})
		
	},
	
	fill: function(){
		
	}

});