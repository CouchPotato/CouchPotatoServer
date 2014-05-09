Page.Log = new Class({

	Extends: PageBase,

	order: 60,
	name: 'log',
	title: 'Show recent logs.',
	has_tab: false,

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
				self.log.set('text', '');
				self.log.adopt(self.createLogElements(json.log));
				self.log.removeClass('loading');

				var nav = new Element('ul.nav', {
					'events': {
						'click:relay(li.select)': function(e, el){
							self.getLogs(parseInt(el.get('text'))-1);
						}
					}
				});

				// Type selection
				new Element('li.filter').grab(
					new Element('select', {
						'events': {
							'change': function(){
								var type_filter = this.getSelected()[0].get('value');
								self.log.set('data-filter', type_filter);
								self.scrollToBottom();
							}
						}
					}).adopt(
						new Element('option', {'value': 'ALL', 'text': 'Show all logs'}),
						new Element('option', {'value': 'INFO', 'text': 'Show only INFO'}),
						new Element('option', {'value': 'DEBUG', 'text': 'Show only DEBUG'}),
						new Element('option', {'value': 'ERROR', 'text': 'Show only ERROR'})
					)
				).inject(nav);

				// Selections
				for (var i = 0; i <= json.total; i++) {
					new Element('li', {
						'text': i+1,
						'class': 'select ' + (nr == i ? 'active': '')
					}).inject(nav);
				}

				// Clear button
				new Element('li.clear', {
					'text': 'clear',
					'events': {
						'click': function(){
							Api.request('logging.clear', {
								'onComplete': function(){
									self.getLogs(0);
								}
							});

						}
					}
				}).inject(nav);

				// Add to page
				nav.inject(self.log, 'top');

				self.scrollToBottom();
			}
		});

	},

	createLogElements: function(logs){

        var elements = [];

        logs.each(function(log){
            elements.include(new Element('div', {
				'class': 'time ' + log.type.toLowerCase(),
                'text': log.time
            }).adopt(
                new Element('span.type', {
                    'text': log.type
                }),
                new Element('span.message', {
                    'text': log.message
                })
            ))
        });

		return elements;
	},

	scrollToBottom: function(){
		new Fx.Scroll(window, {'duration': 0}).toBottom();
	}

});
