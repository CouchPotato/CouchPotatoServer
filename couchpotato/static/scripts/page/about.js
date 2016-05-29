var AboutSettingTab = new Class({

	tab: '',
	content: '',

	initialize: function(){
		var self = this;

		App.addEvent('loadSettings', self.addSettings.bind(self));

	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings');
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
		// WebUI Feature:
		self.hide_about_dirs = !! App.options && App.options.webui_feature && App.options.webui_feature.hide_about_dirs;
		self.hide_about_update = !! App.options && App.options.webui_feature && App.options.webui_feature.hide_about_update;
	},

	createAbout: function(){
		var self = this;

		var millennium = new Date(2008, 7, 16),
			today = new Date(),
			one_day = 1000*60*60*24;


		var about_block;
		self.settings.createGroup({
			'label': 'About This CouchPotato',
			'name': 'variables'
		}).inject(self.content).adopt(
			(about_block = new Element('dl.info')).adopt(
				new Element('dt[text=Version]'),
				self.version_text = new Element('dd.version', {
					'text': 'Getting version...'
				}),

				new Element('dt[text=Updater]'),
				self.updater_type = new Element('dd.updater'),
				new Element('dt[text=ID]'),
				new Element('dd', {'text': App.getOption('pid')})
			)
		);

		if (!self.hide_about_update){
			self.version_text.addEvents({		
				'click': App.checkForUpdate.bind(App, function(json){
					self.fillVersion(json.info);
				}),			
				'mouseenter': function(){
					this.set('text', 'Check for updates');
				},
				'mouseleave': function(){
					self.fillVersion(Updater.getInfo());
				}
			});
		} else {
			// override cursor style from CSS
			self.version_text.setProperty('style', 'cursor: auto');
		}

		if (!self.hide_about_dirs){
			about_block.adopt(
				new Element('dt[text=Directories]'),
				new Element('dd', {'text': App.getOption('app_dir')}),
				new Element('dd', {'text': App.getOption('data_dir')}),
				new Element('dt[text=Startup Args]'),
				new Element('dd', {'html': App.getOption('args')}),
				new Element('dd', {'html': App.getOption('options')})
			);
		}

		if(!self.fillVersion(Updater.getInfo()))
			Updater.addEvent('loaded', self.fillVersion.bind(self));

		self.settings.createGroup({
			'name': 'Help Support CouchPotato'
		}).inject(self.content).adopt(
			new Element('div.usenet').adopt(
				new Element('div.text').adopt(
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
						'href': 'https://www.newshosting.com/partners/?a_aid=couchpotato&a_bid=a0b022df',
						'target': '_blank',
						'text': 'Newshosting'
					}),
					new Element('span', {
						'text': '. For as low as $7.95 per month, you’ll get:'
					})
				),
				new Element('ul').adopt(
					new Element('li.icon-ok', {
						'text': Math.ceil((today.getTime()-millennium.getTime())/(one_day))+" days retention"
					}),
					new Element('li.icon-ok[text=No speed or download limits]'),
					new Element('li.icon-ok[text=Free SSL Encrypted connections]')
				)
			),
			new Element('div.donate', {
				'html': 'Or support me via: <iframe src="https://couchpota.to/donate.html" scrolling="no"></iframe>'
			})
		);

	},

	fillVersion: function(json){
		if(!json) return;
		var self = this;
		var date = new Date(json.version.date * 1000);
		self.version_text.set('text', json.version.hash + (json.version.date ? ' ('+date.toLocaleString()+')' : ''));
		self.updater_type.set('text', (json.version.type != json.branch) ? (json.version.type + ', ' + json.branch) : json.branch);
	}

});

window.addEvent('domready', function(){
	new AboutSettingTab();
});
