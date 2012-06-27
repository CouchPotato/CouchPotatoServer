var SearcherBase = new Class({
	tab: '',
	content: '',

	initialize: function(data){
		var self = this;
		self.methods = ['Torrents', 'Usenet']
		App.addEvent('load', self.addSettings.bind(self))
	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings')
		self.settings.addEvent('create', function(){
			var tab = self.settings.createSubTab('downloadpreference', {
				'label': 'Preference',
				'name': 'downloadpreference'
			}, self.settings.tabs.searcher ,'searcher');

			self.tab = tab.tab;
			self.content = tab.content;

			self.createPreferenceSliders();

		})	
			
	},
		

	/**
	 * preferences
	 */
	createPreferenceSliders: function(){
		var self = this;

		self.api_request = Api.request('downloadpreference.preferredmethod', {
			    'async' : false,
				'onSuccess': function(data){
					if (data['preference'] == "usenet"){
						self.methods = ['Usenet', 'Torrents'];
					}
				},
		});

		self.settings.createGroup({
			'label': 'Download preference',
 		}).adopt(
			new Element('.ctrlHolder#profile_ordering').adopt(
				new Element('label[text=Order]'),
				profile_list = new Element('ul'),
				new Element('p.formHint', {
					'html': 'Indicate your preference of torrents or usenet'
				})
			)
		).inject(self.content)

		var profile_list;
	  
	    Array.each(self.methods, function(method, index){
			var check;
			new Element('li', {'data-id': index}).adopt(
				new Element('span.profile_label', {
					'text': method
				}),
				new Element('span.handle')
			).inject(profile_list);
		});

		// Sortable
		self.profile_sortable = new Sortables(profile_list, {
			'revert': true,
			'handle': '',
			'opacity': 0.5,
			'onComplete': self.savePreferenceOrdering.bind(self)
		});

	},

	savePreferenceOrdering: function(){

        var preferred = $$('.profile_label')[0].get('text').toLowerCase();

		Api.request('settings.save', {
			'data': {
				'section' : 'downloadpreferenceplugin',
				'name' : 'preference',
				'value' : preferred
			}
		});
	}

});

window.Searcher = new SearcherBase();
