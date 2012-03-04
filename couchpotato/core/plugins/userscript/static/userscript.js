Page.Userscript = new Class({

	Extends: PageBase,

	name: 'userscript',
	has_tab: false,

	options: {
		'onOpened': function(){
			App.fireEvent('unload');
			App.getBlock('header').hide();
		}
	},

	indexAction: function(param){
		var self = this;

		self.el.adopt(
			self.frame = new Element('div.frame.loading', {
				'text': 'Loading...'
			})
		);

		var url = window.location.href.split('url=')[1];

		Api.request('userscript.add_via_url', {
			'data': {
				'url': url
			},
			'onComplete': function(json){
				self.frame.empty();
				self.frame.removeClass('loading');

				if(json.error)
					self.frame.set('html', json.error);
				else {
					var item = new Block.Search.Item(json.movie);
					self.frame.adopt(item);
					item.showOptions();
				}
			}
		});

	}

});

var UserscriptSettingTab = new Class({

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

			self.settings.createGroup({
				'label': 'Install the Userscript'
			}).inject(self.settings.tabs.automation.content, 'top').adopt(
				new Element('a', {
					'text': 'Install userscript',
					'href': Api.createUrl('userscript.get')+'couchpotato.user.js',
					'target': '_self'
				})
			);
		});

	}

});

window.addEvent('domready', function(){
	new UserscriptSettingTab();
});

window.addEvent('load', function(){
	var your_version = $(document.body).get('data-userscript_version'),
		latest_version = App.getOption('userscript_version') || '',
		key = 'cp_version_check',
		checked_already = Cookie.read(key);

	if(your_version && your_version < latest_version && checked_already < latest_version){
		if(confirm("Update to the latest Userscript?\nYour version: " + your_version + ', new version: ' + latest_version )){
			document.location = Api.getOption('url')+'userscript.get/?couchpotato.user.js';
		}
		Cookie.write(key, latest_version, {duration: 100});
	}
});
