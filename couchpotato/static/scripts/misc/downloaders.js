var DownloadersBase = new Class({

	Implements: [Events],

	initialize: function(){
		var self = this;

		// Add refresh link for uTorrent download dirs
        App.addEvent('load', function() {
            var setting_page = App.getPage('Settings');
            setting_page.addEvent('create', function(){
                self.addRefreshUtorrentDirsButton( setting_page.tabs.downloaders.groups.utorrent );
            });
        });

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
