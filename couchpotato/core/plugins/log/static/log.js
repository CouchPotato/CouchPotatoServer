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
				self.log.adopt(self.createLogElements(json.log));
				self.log.removeClass('loading');

				new Fx.Scroll(window, {'duration': 0}).toBottom();

				var nav = new Element('ul.nav').inject(self.log, 'top');
				for (var i = 0; i <= json.total; i++) {
					new Element('li', {
						'text': i+1,
						'class': nr == i ? 'active': '',
						'events': {
							'click': function(e){
								self.getLogs(e.target.get('text')-1);
							}
						}
					}).inject(nav);
				}

				new Element('li', {
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
				}).inject(nav)
			}
		});

	},

	createLogElements: function(logs){

        var elements = [];

        logs.each(function(log){
            elements.include(new Element('div.time', {
                'text': log.time
            }).grab(
                new Element('span', {
                    'class': log.type.toLowerCase(),
                    'text': log.message
                })
            ))
        });

		return elements;
	}

});
