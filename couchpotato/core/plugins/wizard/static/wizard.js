var WizardBase = new Class({

	Implements: [Options, Events],

	initialize: function(steps){
		var self = this;

		self.steps = steps;
		self.start();

	},

	start: function(){
		
		

	},

	nextStep: function(){

	},

	previousStep: function(){

	}

});

WizardBase.Screen = new Class({
	
	initialize: function(data){
		var self = this;
		
		self.data = data;
		self.create()
		
	},
	
	create: function(){
		var self = this;
		
		self.el = new Element('div.')
		
		
	},
	
	destroy: function(){
		this.el.destroy();
		
		return this
	}
	
})

window.Wizard = new WizardBase([
	{
		'title': 'Fill in your username and password',
		'Description': 'Outside blabla',
		'tab': 'general',
		'fields': ['username', 'password']
	},
	{
		'title': 'What do you use to download your movies',
		'answers': [
			{'name': 'nzb', 'label': 'Usenet'},
			{'name': 'torrent', 'label': 'Torrents'}
		]
	},
	{
		'title': 'Do you have a login for any of the following sites',
		'tab': 'providers',
		'needs': function(){
			return self.config_nzb || self.config_torrent
		}
	}
])
