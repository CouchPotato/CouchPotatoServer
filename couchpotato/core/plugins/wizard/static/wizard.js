Page.Wizard = new Class({

	Extends: PageBase,

	name: 'wizard',
	has_tab: false,

	options: {
		'onOpened': function(){
			App.fireEvent('unload');
			App.getBlock('header').hide();
		}
	},

	initialize: function(options){
		var self = this;
		self.parent(options);

		// Create steps
		self.steps = [
			{'step':'index', 'title': 'Welcome'},
			{'step':'step1', 'title': 'Security'},
			{'step':'step2', 'title': 'Downloaders'}
		]

		self.breadcrumbs = new Element('ul').inject(self.el);
		Object.each(self.steps, function(step, nr){
			step.el = new Element('li', {
				'class': (nr == 0 ? 'active ' : '') + 'step_'+step.step,
				'data-nr': nr,
				'text': step.title
			}).inject(self.breadcrumbs)
		});

		p(self.steps);

	},

	nextStep: function(e){
		var self = this;
		(e).stop();

		var next = (self.current_step || 0)+1;
		var step = self.steps[next];
		self.breadcrumbs.getElement('.active').removeClass('active');
		step.el.addClass('active');

		self.openUrl('/'+self.name+'/'+step.step+'/');

		p('nextStep');
	},

	previousStep: function(){
		var self = this;

		p('previousStep');
	},

	stop: function(){
		var self = this;
		(e).stop();

		p('close');
	},

	// Welcome
	indexAction: function(){
		var self = this;

		var step = new Page.Wizard.Step('welcome', {
			'title': 'Welcome to the CouchPotato wizard',
			'description': 'Before you can start creating that butt-formed hole in you couch, you must complete the following wizard.',
			'groups': [
				{
					'content': new Element('a.button.green', {
						'text': 'Go to the first step',
						'events': {
							'click': self.nextStep.bind(self)
						}
					})
				},
				{
					'title': 'Skip wizard',
					'description': 'You can always activate the wizard from within the settings page',
					'content': new Element('a.button.orange', {
						'text': 'I already know how this works, I\'ll fill it in manually, thanks.',
						'events': {
							'click': self.stop.bind(self)
						}
					})
				}
			]
		});

		return [self.breadcrumbs, step]

	},

	// Username password browser
	step1Action: function(){
		var self = this;

		var step = new Page.Wizard.Step('security', {
			'title': 'Security',
			'description': 'Before you can start creating that butt-formed hole in you couch, you must complete the following wizard.',
			'groups': [
				{
					'title': 'Fill in your username and password',
					'description': 'Keep blank if you don\'t want to secure CP.',
					'fields': ['core.username', 'core.password']
				},
				{
					'title': 'Launch the browser when CP starts',
					'fields': ['core.launch_browser']
				}
			]
		})

		return [self.breadcrumbs, step]
	},

	// NZB Torrent, downloaders
	step2Action: function(){
		var options = {
			'title': 'What do you use to download your movies',
			'answers': [
				{'name': 'nzb', 'label': 'Usenet'},
				{'name': 'torrent', 'label': 'Torrents'}
			]
		}
	}

	// NZB show affiliates
		// NZB: retention
		// Downloaders
		// Providers
			// Automated registration nzb.su via email api
		// Renamer
		// Userscript, depending on browser
		// Extras:
			// Notifications
			// Metadata

});

Page.Wizard.Step = new Class({

	Implements: [Options],

	initialize: function(name, options){
		var self = this;
		self.setOptions(options);

		self.name = name;
		self.create();

	},

	create: function(){
		var self = this;

		// Main element
		self.el = new Element('div.step').addClass(self.name || '');

		self.createTitleDescription(self.options, self.el);

		// Groups
		if(self.options.groups){
			self.groups = new Element('div.groups').inject(self.el);
			self.options.groups.each(self.createGroup.bind(self));
		}

	},

	createGroup: function(options){
		var self = this;

		var group = new Element('div.group').inject(self.groups);

		self.createTitleDescription(options, group);

		// Content
		if(options.content)
			options.content.inject(group);

		// Fields
		if(options.fields)
			options.fields.each(self.createField.bind(self))


	},

	createField: function(field){

	},

	createTitleDescription: function(options, inject_in){
		var self = this;


		// Title
		if(options.title)
			self.title = new Element('div.title', {
				'text': options.title
			}).inject(inject_in);

		// Descriptions
		if(options.description)
			self.title = new Element('div.description', {
				'text': options.description
			}).inject(inject_in);

	},

	toElement: function(){
		return this.el;
	}

})

window.addEvent('domready', function(){

	// Check if wizard is enabled

});
