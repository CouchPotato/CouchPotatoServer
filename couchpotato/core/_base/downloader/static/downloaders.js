var DownloadersBase = new Class({

	Implements: [Events],

	initialize: function(){
		var self = this;

		// Add test buttons to settings page
		App.addEvent('loadSettings', self.addTestButtons.bind(self));

	},

	// Downloaders setting tests
	addTestButtons: function(){
		var self = this;

		var setting_page = App.getPage('Settings');
		setting_page.addEvent('create', function(){
			Object.each(setting_page.tabs.downloaders.groups, self.addTestButton.bind(self));
		});

	},

	addTestButton: function(fieldset, plugin_name){
		var self = this,
			button_name = self.testButtonName(fieldset);

		if(button_name.contains('Downloaders')) return;

		new Element('.ctrlHolder.test_button').grab(
			new Element('a.button', {
				'text': button_name,
				'events': {
					'click': function(){
						var button = fieldset.getElement('.test_button .button');
							button.set('text', 'Connecting...');

						Api.request('download.'+plugin_name+'.test', {
							'onComplete': function(json){

								button.set('text', button_name);

								var message;
								if(json.success){
									message = new Element('span.success', {
										'text': 'Connection successful'
									}).inject(button, 'after');
								}
								else {
									var msg_text = 'Connection failed. Check logs for details.';
									if(json.hasOwnProperty('msg')) msg_text = json.msg;
									message = new Element('span.failed', {
										'text': msg_text
									}).inject(button, 'after');
								}

								requestTimeout(function(){
									message.destroy();
								}, 3000);
							}
						});
					}
				}
			})
		).inject(fieldset);

	},

	testButtonName: function(fieldset){
		var name = fieldset.getElement('h2 .group_label').get('text');
		return 'Test '+name;
	}

});

var Downloaders = new DownloadersBase();
