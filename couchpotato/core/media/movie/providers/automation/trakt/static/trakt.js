var TraktAutomation = new Class({

	initialize: function(){
		var self = this;

		App.addEvent('loadSettings', self.addRegisterButton.bind(self));
	},

	addRegisterButton: function(){
		var self = this,
			setting_page = App.getPage('Settings');

		setting_page.addEvent('create', function(){

		 	var fieldset = setting_page.tabs.automation.groups.trakt_automation,
		 		l = window.location;

			var trakt_set = 0;
		 	fieldset.getElements('input[type=text]').each(function(el){
		 		trakt_set += +(el.get('value') !== '');
		 	});

			new Element('.ctrlHolder').adopt(

			 	// Unregister button
			 	(trakt_set > 0) ?
			 		[
						self.unregister = new Element('a.button.red', {
							'text': 'Unregister',
							'events': {
								'click': function(){
									fieldset.getElements('input[name*=oauth_token]').set('value', '').fireEvent('change');

									self.unregister.destroy();
									self.unregister_or.destroy();
								}
							}
						}),
						self.unregister_or = new Element('span[text=or]')
					]
			 	: null,

				// Register button
				new Element('a.button', {
					'text': trakt_set > 0 ? 'Register a different account' : 'Register your trakt.tv account',
					'events': {
						'click': function(){
							Api.request('automation.trakt.auth_url', {
								'data': {
									'host': l.protocol + '//' + l.hostname + (l.port ? ':' + l.port : '')
								},
								'onComplete': function(json){
									window.location = json.url;
								}
							});
						}
					}
				})

			).inject(fieldset);
		});

	}

});

new TraktAutomation();
