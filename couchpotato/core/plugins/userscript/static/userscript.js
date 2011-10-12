Page.Userscript = new Class({

	Extends: PageBase,

	name: 'userscript',
	has_tab: false,

	options: {
		'onOpened': function(){
			App.stopLoadTimer();
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