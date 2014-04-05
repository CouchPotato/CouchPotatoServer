var TwitterNotification = new Class({

	initialize: function(){
		var self = this;
		App.addEvent('loadSettings', self.addRegisterButton.bind(self));
	},

	addRegisterButton: function(){
		var self = this;

		 var setting_page = App.getPage('Settings');
		 setting_page.addEvent('create', function(){

		 	var fieldset = setting_page.tabs.notifications.groups.twitter,
		 		l = window.location;

			var twitter_set = 0;
		 	fieldset.getElements('input[type=text]').each(function(el){
		 		twitter_set += +(el.get('value') != '');
		 	});


			new Element('.ctrlHolder').adopt(

			 	// Unregister button
			 	(twitter_set > 0) ?
			 		[
						self.unregister = new Element('a.button.red', {
							'text': 'Unregister "'+fieldset.getElement('input[name*=screen_name]').get('value')+'"',
							'events': {
								'click': function(){
									fieldset.getElements('input[type=text]').set('value', '').fireEvent('change');

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
					'text': twitter_set > 0 ? 'Register a different account' : 'Register your Twitter account',
					'events': {
						'click': function(){
							Api.request('notify.twitter.auth_url', {
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
			).inject(fieldset.getElement('.test_button'), 'before');
		})

	}

});

window.addEvent('domready', function(){
	new TwitterNotification();
});
