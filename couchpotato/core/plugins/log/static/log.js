Page.Log = new Class({

	Extends: PageBase,

	name: 'log',
	title: 'Show recent logs.',
	has_tab: false,

	initialize: function(options){
		var self = this;
		self.parent(options)


		App.getBlock('more').addLink(new Element('a', {
			'href': App.createUrl(self.name),
			'text': self.name.capitalize(),
			'title': self.title
		}))

	},

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
				self.log.set('html', self.addColors(json.log));
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
				};

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

	addColors: function(text){
		var self = this;

		text = text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/\u001b\[31m/gi, '</span><span class="error">')
			.replace(/\u001b\[36m/gi, '</span><span class="debug">')
			.replace(/\u001b\[33m/gi, '</span><span class="debug">')
			.replace(/\u001b\[0m\n/gi, '</span><span class="time">')
			.replace(/\u001b\[0m/gi, '</span><span>')

		return '<span class="time">' + text + '</span>';
	}

})