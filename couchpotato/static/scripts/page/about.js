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
			)
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