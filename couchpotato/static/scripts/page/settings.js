Page.Settings = new Class({

	Extends: PageBase,

	name: 'settings',
	title: 'Change settings.',

	tabs: {
		'general': {
			'label': 'General'
		},
		'providers': {
			'label': 'Providers'
		}
	},

	open: function(action, params){
		var self = this
		self.action = action;
		self.params = params;

		if(!self.data)
			self.getData(self.create.bind(self))
		else
			self.openTab(action);
	},

	openTab: function(action){
		var self = this;
		action = action || self.action

		if(self.current)
			self.toggleTab(self.current, true);

		self.toggleTab(action)
		self.current = action;

	},

	toggleTab: function(tab_name, hide){
		var self = this;

		var a = hide ? 'removeClass' : 'addClass';
		var c = 'active';

		var t = self.tabs[tab_name] || self.tabs[self.action] || self.tabs.general;
			t.tab[a](c);
			t.content[a](c);

	},

	getData: function(onComplete){
		var self = this;

		if(onComplete)
			Api.request('settings', {
				'useSpinner': true,
				'spinnerOptions': {
					'target': self.el
				},
				'onComplete': function(json){
					self.data = json;
					onComplete(json);
				}
			})

		return self.data;
	},

	getValue: function(section, name){
		var self = this;
		try {
			return self.data.values[section][name] || '';
		}
		catch(e){
			return ''
		}
	},

	showAdvanced: function(){
		var self = this;

		var c = self.advanced_toggle.checked ? 'addClass' : 'removeClass';
		self.el[c]('show_advanced')
	},

	create: function(json){
		var self = this

		self.el.adopt(
			self.tabs_container = new Element('ul.tabs'),
			self.containers = new Element('form.uniForm.containers').adopt(
				new Element('label.advanced_toggle').adopt(
					new Element('span', {
						'text': 'Show advanced settings'
					}),
					self.advanced_toggle = new Element('input[type=checkbox]', {
						'events': {
							'change': self.showAdvanced.bind(self)
						}
					})
				)
			)
		);

		// Create tabs
		Object.each(self.tabs, function(tab, tab_name){
			self.createTab(tab_name, tab)
		});

		// Add content to tabs
		Object.each(json.options, function(section, section_name){

			// Add groups to content
			section.groups.sortBy('order').each(function(group){

				// Create the group
				var group_el = self.createGroup(group).inject(self.tabs[group.tab].content);

				self.tabs[group.tab].groups[group.name] = group_el

				// Add options to group
				group.options.sortBy('order').each(function(option){
					var class_name = (option.type || 'input').capitalize();
					var input = new Option[class_name](self, section_name, option.name, option);
						input.inject(group_el);
				});

			});
		});



		self.fireEvent('create');
		self.openTab();

	},

	createTab: function(tab_name, tab){
		var self = this;

		if(self.tabs[tab_name] && self.tabs[tab_name].tab)
			return self.tabs[tab_name].tab

		var tab_el = new Element('li').adopt(
			new Element('a', {
				'href': '/'+self.name+'/'+tab_name+'/',
				'text': tab.label.capitalize()
			})
		).inject(self.tabs_container);

		if(!self.tabs[tab_name])
			self.tabs[tab_name] = {
				'label': tab.label
			}

		self.tabs[tab_name] = Object.merge(self.tabs[tab_name], {
			'tab': tab_el,
			'content': new Element('div.tab_content').inject(self.containers),
			'groups': {}
		})

		return self.tabs[tab_name]

	},

	createGroup: function(group){
		var self = this;

		var group_el = new Element('fieldset', {
			'class': group.advanced ? 'inlineLabels advanced' : 'inlineLabels'
		}).adopt(
			new Element('h2', {
				'text': group.label
			}).adopt(
				new Element('span.hint', {
					'text': group.description
				})
			)
		)

		return group_el
	}

});

var OptionBase = new Class({

	Implements: [Options, Events],

	klass: 'textInput',
	focused_class : 'focused',
	save_on_change: true,

	initialize: function(parent, section, name, options){
		var self = this
		self.setOptions(options)

		self.page = parent;
		self.section = section;
		self.name = name;

		self.createBase();
		self.create();
		self.createHint();
		self.setAdvanced();

		// Add focus events
		self.input.addEvents({
			'change': self.changed.bind(self),
			'keyup': self.changed.bind(self)
		});

	},

	/**
	 * Create the element
	 */
	createBase: function(){
		var self = this
		self.el = new Element('div.ctrlHolder')
	},

	create: function(){},

	setAdvanced: function(){
		this.el.addClass(this.options.advanced ? 'advanced': '')
	},

	createHint: function(){
		var self = this;
		if(self.options.description)
			new Element('p.formHint', {
				'text': self.options.description
			}).inject(self.el);
	},

	// Element has changed, do something
	changed: function(){
		var self = this;

		if(self.getValue() != self.previous_value){
			if(self.save_on_change){
				if(self.changed_timer) clearTimeout(self.changed_timer);
				self.changed_timer = self.save.delay(300, self);
			}
			self.fireEvent('change')
		}

	},

	save: function(){
		var self = this;

		Api.request('setting.save', {
			'data': {
				'section': self.section,
				'name': self.name,
				'value': self.getValue()
			},
			'useSpinner': true,
			'spinnerOptions': {
				'target': self.el
			},
			'onComplete': self.saveCompleted.bind(self)
		});

	},

	saveCompleted: function(json){
		var self = this;

		var sc = json.success ? 'save_success' : 'save_failed';

		self.previous_value = self.getValue();
		self.el.addClass(sc);

		(function(){
			self.el.removeClass(sc);
		}).delay(3000, self);
	},

	setName: function(name){
		this.name = name;
	},

	postName: function(){
		var self = this;
		return self.section +'['+self.name+']';
	},

	getValue: function(){
		var self = this;
		return self.input.get('value');
	},

	getSettingValue: function(){
		var self = this;
		return self.page.getValue(self.section, self.name);
	},

	inject: function(el, position){
		this.el.inject(el, position);
		return this.el;
	},

	toElement: function(){
		return this.el;
	}
})

var Option = {}
Option.String = new Class({
	Extends: OptionBase,

	type: 'input',

	create: function(){
		var self = this

		self.el.adopt(
			new Element('label', {
				'text': self.options.label
			}),
			self.input = new Element('input', {
				'type': 'text',
				'name': self.postName(),
				'value': self.getSettingValue()
			})
		);
	}
});

Option.Dropdown = new Class({
	Extends: OptionBase,

	create: function(){
		var self = this

		new Element('label', {
			'text': self.options.label
		}).adopt(
			self.input = new Element('select', {
				'name': self.postName()
			})
		).inject(self.el)

		Object.each(self.options.values, function(label, value){
			new Element('option', {
				'text': label,
				'value': value
			}).inject(self.input)
		})

		self.input.set('value', self.getSettingValue());
	}
});

Option.Checkbox = new Class({
	Extends: OptionBase,

	type: 'checkbox',

	create: function(){
		var self = this;

		var randomId = 'option-'+Math.floor(Math.random()*1000000)

		new Element('label', {
			'text': self.options.label,
			'for': randomId
		}).inject(self.el);

		self.input = new Element('input', {
			'type': 'checkbox',
			'value': self.getSettingValue(),
			'checked': self.getSettingValue() !== undefined,
			'id': randomId
		}).inject(self.el);
	}
});

Option.Bool = new Class({
	Extends: Option.Checkbox
});

Option.Int = new Class({
	Extends: Option.String
});

Option.Directory = new Class({

	Extends: OptionBase,

	type: 'span',
	browser: '',
	save_on_change: false,

	create: function(){
		var self = this;


		self.el.adopt(
			new Element('label', {
				'text': self.options.label
			}),
			self.input = new Element('span', {
				'text': self.getSettingValue(),
				'events': {
					'click': self.showBrowser.bind(self),
					'outerClick': self.hideBrowser.bind(self)
				}
			})
		);

		self.cached = {};
	},

	showBrowser: function(){
		var self = this;

		if(!self.browser)
			self.browser = new Element('div.directory_list').adopt(
				self.dir_list = new Element('ul')
			).inject(self.input, 'after')

		self.getDirs()
		self.browser.show()
	},

	hideBrowser: function(){
		this.browser.hide()
	},

	fillBrowser: function(json){
		var self = this;

		var c = self.getCurrentDir();
		var v = self.input.get('value');
		var add = true

		if(!json){
			json = self.cached[c];
		}
		else {
			self.cached[c] = json;
		}

		self.dir_list.empty();
		json.dirs.each(function(dir){
			if(dir.indexOf(v) != -1){
				new Element('li', {
					'text': dir
				}).inject(self.dir_list)

				if(add){
					self.input.insertAtCursor(dir.substring(v.length), true);
					add = false
				}
			}
		})
	},

	getDirs: function(){
		var self = this;

		var c = self.getCurrentDir();

		if(self.cached[c]){
			self.fillBrowser()
		}
		else {
			Api.request('directory.list', {
				'data': {
					'path': c
				},
				'onComplete': self.fillBrowser.bind(self)
			})
		}
	},

	getCurrentDir: function(){
		var self = this;

		var v = self.input.get('value');
		var sep = Api.getOption('path_sep');
		var dirs = v.split(sep);
			dirs.pop();

		return dirs.join(sep)
	},

	getValue: function(){
		var self = this;
		return self.input.get('text');
	}
});
