var AboutSettingTab = new Class({

	tab: '',
	content: '',

	initialize: function(){
		var self = this;

		App.addEvent('load', self.addSettings.bind(self))

	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings')
		self.settings.addEvent('create', function(){
			var tab = self.settings.createTab('about', {
				'label': 'About',
				'name': 'about'
			});

			self.tab = tab.tab;
			self.content = tab.content;

			self.createAbout();

		});

		self.settings.default_action = 'about';

	},

	createAbout: function(){
		var self = this;

		var millennium = new Date(2008, 7, 16),
			today = new Date(),
			one_day = 1000*60*60*24;

		self.settings.createGroup({
			'label': 'About This CouchPotato',
			'name': 'variables'
		}).inject(self.content).adopt(
			new Element('dl.info').adopt(
				new Element('dt[text=Version]'),
				self.version_text = new Element('dd.version', {
					'text': 'Getting version...',
					'events': {
						'click': App.checkForUpdate.bind(App, function(json){
							self.fillVersion(json.info)
						}),
						'mouseenter': function(){
							this.set('text', 'Check for updates')
						},
						'mouseleave': function(){
							self.fillVersion(Updater.getInfo())
						}
					}
				}),
				new Element('dt[text=ID]'),
				new Element('dd', {'text': App.getOption('pid')}),
				new Element('dt[text=Directories]'),
				new Element('dd', {'text': App.getOption('app_dir')}),
				new Element('dd', {'text': App.getOption('data_dir')}),
				new Element('dt[text=Startup Args]'),
				new Element('dd', {'html': App.getOption('args')}),
				new Element('dd', {'html': App.getOption('options')})
			)
		);

		if(!self.fillVersion(Updater.getInfo()))
			Updater.addEvent('loaded', self.fillVersion.bind(self))

		self.settings.createGroup({
			'name': 'Help Support CouchPotato'
		}).inject(self.content).adopt(
			new Element('div.usenet').adopt(
				new Element('span', {
					'text': 'Help support CouchPotato and save some money for yourself by signing up for an account at'
				}),
				new Element('a', {
					'href': 'https://usenetserver.com/partners/?a_aid=couchpotato&a_bid=3f357c6f',
					'target': '_blank',
					'text': 'UsenetServer'
				}),
				new Element('span[text=or]'),
				new Element('a', {
					'href': 'http://www.newshosting.com/partners/?a_aid=couchpotato&a_bid=a0b022df',
					'target': '_blank',
					'text': 'Newshosting'
				}),
				new Element('span', {
					'text': '. For as low as $7.95 per month, you’ll get:'
				}),
				new Element('ul').adopt(
					new Element('li', {
						'text': Math.ceil((today.getTime()-millennium.getTime())/(one_day))+" days retention"
					}),
					new Element('li[text=No speed or download limits]'),
					new Element('li[text=Free SSL Encrypted connections]')
				)
			),
			new Element('div.donate', {
				'html':
				'Or, buy me a (24 pack) Pepsi, for while I\'m coding ;)' +
				'<form action="https://www.paypal.com/cgi-bin/webscr" method="post">' +
					'<input type="hidden" name="cmd" value="_s-xclick">' +
					'<input type="hidden" name="encrypted" value="-----BEGIN PKCS7-----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-----END PKCS7-----">' +
					'<input type="image" src="https://www.paypal.com/en_US/i/btn/btn_donate_LG.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">' +
				'</form>'
			})
		);

	},

	fillVersion: function(json){
		if(!json) return;
		var self = this;
		var date = new Date(json.version.date * 1000);
		self.version_text.set('text', json.version.hash + ' ('+date.toUTCString()+')');
	}

});

window.addEvent('domready', function(){
	new AboutSettingTab();
});