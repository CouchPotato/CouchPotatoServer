var DownloadersBase = new Class({

	Implements: [Events],

	initialize: function(){
		var self = this;

		// Add test buttons to settings page
		App.addEvent('load', self.addTestButtons.bind(self));

		// Add refresh link for uTorrent download dirs
        App.addEvent('load', function() {
            var setting_page = App.getPage('Settings');
            setting_page.addEvent('create', function(){
                self.addRefreshUtorrentDirsButton( setting_page.tabs.downloaders.groups.utorrent );
            });
        });

	},

	// Downloaders setting tests
	addTestButtons: function(){
		var self = this;

		var setting_page = App.getPage('Settings');
		setting_page.addEvent('create', function(){
			Object.each(setting_page.tabs.downloaders.groups, self.addTestButton.bind(self))
		})

	},

	addTestButton: function(fieldset, plugin_name){
		var self = this,
			button_name = self.testButtonName(fieldset);

		if(button_name.contains('Downloaders')) return;

		Api.request('download.'+plugin_name+'.is_testable',  {
			'onComplete': function(json){
                if(json.success){
                    // Only add test button if downloader is testable
                    new Element('.ctrlHolder.test_button').adopt(
                        new Element('a.button', {
                            'text': button_name,
                            'events': {
                                'click': function(){
                                    var button = fieldset.getElement('.test_button .button');
                                        button.set('text', 'Connecting...');

                                    Api.request('download.'+plugin_name+'.test', {
                                        'onComplete': function(json){

                                            button.set('text', button_name);

                                            if(json.success){
                                                var message = new Element('span.success', {
                                                    'text': 'Connection successful'
                                                }).inject(button, 'after')
                                            }
                                            else {
                                                var message = new Element('span.failed', {
                                                    'text': 'Connection failed. Check logs for details.'
                                                }).inject(button, 'after')
                                            }

                                            (function(){
                                                message.destroy();
                                            }).delay(3000)
                                        }
                                    });
                                }
                            }
                        })
                    ).inject(fieldset);
                }
			}
		});

	},

	testButtonName: function(fieldset){
		var name = String(fieldset.getElement('h2').innerHTML).substring(0,String(fieldset.getElement('h2').innerHTML).indexOf("<span"));
		return 'Test '+name;
	},

	addRefreshUtorrentDirsButton: function(fieldset) {
	    var self = this;

	    var uTorrentCtrl = $(fieldset.getElement('div.ctrlHolder.utorrent_download_directory'));
	    uTorrentCtrl.getElement('p.formHint').grab(new Element('a', {
	        'text': 'Refresh',
	        'style': 'padding-left: 0.3em; padding-right: 0.3em;',
	        'events': { 'click': function(ev) {
	            ev.preventDefault();
	            ev.target.set('text','Refreshing...');

	            Api.request('download.utorrent.get_dirs', {
                    'onComplete': function(json){

                        ev.target.set('text','Refresh');

                        if(json.success){
                            self.updateUtorrentDirs( uTorrentCtrl.getElement('div.select'), json.directories );
                            var message = new Element('span.success', {
                                'text': 'Done!'
                            }).inject(ev.target, 'after');
                        }
                        else {
                            var message = new Element('span.failed', {
                                'text': 'Connection failed'
                            }).inject(ev.target, 'after');
                        }

                        (function(){
                            message.destroy();
                        }).delay(3000)
                    }
                });
	        }}
	    }));
	},

	updateUtorrentDirs: function(el_select, dirs) {
	    var new_options = [];

        Object.each( dirs, function(value) {
            new_options.push( new Element('option',{
                'text': value,
                'value': value
            }));
        });

        el_select.fireEvent('update_options',[new_options]);
	}

});

window.Downloaders = new DownloadersBase();
