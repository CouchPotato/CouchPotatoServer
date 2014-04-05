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

	indexAction: function(){
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
					var item = new Block.Search.MovieItem(json.movie);
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

		App.addEvent('loadSettings', self.addSettings.bind(self))

	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings');
		self.settings.addEvent('create', function(){

			var host_url = window.location.protocol + '//' + window.location.host;

			self.settings.createGroup({
				'name': 'userscript',
				'label': 'Install the browser extension or bookmarklet',
				'description': 'Easily add movies via imdb.com, appletrailers and more'
			}).inject(self.settings.tabs.automation.content, 'top').adopt(
				new Element('a.userscript.button', {
					'text': 'Install extension',
					'href': 'https://couchpota.to/extension/',
					'target': '_blank'
				}),
				new Element('span.or[text=or]'),
				new Element('span.bookmarklet').adopt(
					new Element('a.button.green', {
						'text': '+CouchPotato',
						'href': "javascript:void((function(){var e=document.createElement('script');e.setAttribute('type','text/javascript');e.setAttribute('charset','UTF-8');e.setAttribute('src','" +
								host_url + Api.createUrl('userscript.bookmark') +
								"?host="+ encodeURI(host_url + Api.createUrl('userscript.get')+randomString()+'/') +
						 		"&r='+Math.random()*99999999);document.body.appendChild(e)})());",
						'target': '',
						'events': {
							'click': function(e){
								(e).stop();
								alert('Drag it to your bookmark ;)')
							}
						}
					}),
					new Element('span', {
						'text': '⇽ Drag this to your bookmarks'
					})
				)
			).setStyles({
				'background-image': "url('https://couchpota.to/media/images/userscript.gif')"
			});

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
			document.location = Api.createUrl('userscript.get')+randomString()+'/couchpotato.user.js';
		}
		Cookie.write(key, latest_version, {duration: 100});
	}
});
