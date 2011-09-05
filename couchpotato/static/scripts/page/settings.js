Page.Settings = new Class({

	Extends: PageBase,

	name: 'settings',
	title: 'Change settings.',

	tabs: {
		'general': {},
		'searcher': {},
		'providers': {},
		'downloaders': {},
		'notifications': {},
		'renamer': {}
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
		var action = action || self.action;

		if(self.current)
			self.toggleTab(self.current, true);

		var tab = self.toggleTab(action)
		self.current = tab == self.tabs.general ? 'general' : action;

	},

	toggleTab: function(tab_name, hide){
		var self = this;

		var a = hide ? 'removeClass' : 'addClass';
		var c = 'active';

		var t = self.tabs[tab_name] || self.tabs[self.action] || self.tabs.general;
			t.tab[a](c);
			t.content[a](c);

		return t
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
			return self.data.values[section][name];
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
					self.advanced_toggle = new Element('input[type=checkbox].inlay', {
						'events': {
							'change': self.showAdvanced.bind(self)
						}
					})
				)
			)
		);

		new Form.Check(self.advanced_toggle, {
			'onChange': self.showAdvanced.bind(self)
		})

		// Create tabs
		Object.each(self.tabs, function(tab, tab_name){
			self.createTab(tab_name, tab)
		});

		// Add content to tabs
		Object.each(json.options, function(section, section_name){

			// Add groups to content
			section.groups.sortBy('order').each(function(group){

				// Create the group
				if(!self.tabs[group.tab].groups[group.name]){
					var group_el = self.createGroup(group)
						.inject(self.tabs[group.tab].content)
						.addClass('section_'+section_name);
					self.tabs[group.tab].groups[group.name] = group_el
				}

				// Add options to group
				group.options.sortBy('order').each(function(option){
					var class_name = (option.type || 'string').capitalize();
					var input = new Option[class_name](self, section_name, option.name, option);
						input.inject(self.tabs[group.tab].groups[group.name]);
						input.fireEvent('injected')
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

		var label = (tab.label || tab.name || tab_name).capitalize()
		var tab_el = new Element('li').adopt(
			new Element('a', {
				'href': '/'+self.name+'/'+tab_name+'/',
				'text': label
			}).adopt()
		).inject(self.tabs_container);

		if(!self.tabs[tab_name])
			self.tabs[tab_name] = {
				'label': label
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
				'text': (group.label || group.name).capitalize()
			}).adopt(
				new Element('span.hint', {
					'html': group.description
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

		self.addEvent('injected', self.afterInject.bind(self))

	},

	/**
	 * Create the element
	 */
	createBase: function(){
		var self = this
		self.el = new Element('div.ctrlHolder')
	},

	create: function(){},

	createLabel: function(){
		var self = this;
		return new Element('label', {
			'text': (self.options.label || self.options.name).capitalize()
		})
	},

	setAdvanced: function(){
		this.el.addClass(this.options.advanced ? 'advanced': '')
	},

	createHint: function(){
		var self = this;
		if(self.options.description)
			new Element('p.formHint', {
				'html': self.options.description
			}).inject(self.el);
	},

	afterInject: function(){},

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

		Api.request('settings.save', {
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

	type: 'string',

	create: function(){
		var self = this

		self.el.adopt(
			self.createLabel(),
			self.input = new Element('input.inlay', {
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

		self.el.adopt(
			self.createLabel(),
			self.input = new Element('select', {
				'name': self.postName()
			})
		)

		Object.each(self.options.values, function(value){
			new Element('option', {
				'text': value[0],
				'value': value[1]
			}).inject(self.input)
		})

		self.input.set('value', self.getSettingValue());

		var dd = new Form.Dropdown(self.input, {
			'onChange': self.changed.bind(self)
		});
		self.input = dd.input;
	}
});

Option.Checkbox = new Class({
	Extends: OptionBase,

	type: 'checkbox',

	create: function(){
		var self = this;

		var randomId = 'r-'+randomString()

		self.el.adopt(
			self.createLabel().set('for', randomId),
			self.input = new Element('input.inlay', {
				'name': self.postName(),
				'type': 'checkbox',
				'checked': self.getSettingValue(),
				'id': randomId
			})
		);

		new Form.Check(self.input, {
			'onChange': self.changed.bind(self)
		});

	},

	getValue: function(){
		var self = this;
		return +self.input.checked;
	}
});

Option.Password = new Class({
	Extends: Option.String,
	type: 'password',

	create: function(){
		var self = this;

		self.parent()
		self.input.set('type', 'password')
	}
});

Option.Bool = new Class({
	Extends: Option.Checkbox
});

Option.Enabler = new Class({
	Extends: Option.Bool,

	create: function(){
		var self = this;

		self.el.adopt(
			self.input = new Element('input.inlay', {
				'type': 'checkbox',
				'checked': self.getSettingValue(),
				'id': 'r-'+randomString(),
				'events': {
					'change': self.checkState.bind(self)
				}
			})
		);

		new Form.Check(self.input, {
			'onChange': self.changed.bind(self)
		});
	},

	changed: function(){
		this.parent();
		this.checkState();
	},

	checkState: function(){
		var self = this;

		self.parentFieldset[ self.getValue() ? 'removeClass' : 'addClass']('disabled');
	},

	afterInject: function(){
		var self = this;

		self.parentFieldset = self.el.getParent('fieldset')
		self.el.inject(self.parentFieldset, 'top')
		self.checkState()
	}

});

Option.Int = new Class({
	Extends: Option.String
});

Option.Directory = new Class({

	Extends: OptionBase,

	type: 'span',
	browser: '',
	save_on_change: false,
	use_cache: false,

	create: function(){
		var self = this;

		self.el.adopt(
			self.createLabel(),
			new Element('span.directory.inlay', {
				'events': {
					'click': self.showBrowser.bind(self)
				}
			}).adopt(
				self.input = new Element('span', {
					'text': self.getSettingValue()
				})
			)
		);

		self.cached = {};
	},

	selectDirectory: function(dir){
		var self = this;

		self.input.set('text', dir);

		self.getDirs()
	},

	previousDirectory: function(e){
		var self = this;

		self.selectDirectory(self.getParentDir())
	},

	showBrowser: function(){
		var self = this;

		if(!self.browser){
			self.browser = new Element('div.directory_list').adopt(
				new Element('div.pointer'),
				new Element('div.actions').adopt(
					self.back_button = new Element('a.back', {
						'html': '',
						'events': {
							'click': self.previousDirectory.bind(self)
						}
					}),
					new Element('label', {
						'text': 'Hidden folders'
					}).adopt(
						self.show_hidden = new Element('input[type=checkbox].inlay', {
							'events': {
								'change': self.getDirs.bind(self)
							}
						})
					)
				),
				self.dir_list = new Element('ul', {
					'events': {
						'click:relay(li)': function(e, el){
							(e).stop();
							self.selectDirectory(el.get('data-value'))
						},
						'mousewheel': function(e){
							(e).stopPropagation();
						}
					}
				}),
				new Element('div.actions').adopt(
					new Element('a.cancel', {
						'text': 'Cancel',
						'events': {
							'click': self.hideBrowser.bind(self)
						}
					}),
					new Element('span', {
						'text': 'or'
					}),
					self.save_button = new Element('a.button.save', {
						'text': 'Save',
						'events': {
							'click': function(e){
								self.hideBrowser(e, true)
							}
						}
					})
				)
			).inject(self.el)

			new Form.Check(self.show_hidden);
		}

		self.initial_directory = self.input.get('text');

		self.getDirs()
		self.browser.show()
		self.el.addEvent('outerClick', self.hideBrowser.bind(self))
	},

	hideBrowser: function(e, save){
		var self = this;
		(e).stop();

		if(save)
			self.save()
		else
			self.input.set('text', self.initial_directory);

		self.browser.hide()
		self.el.removeEvent('outerClick', self.hideBrowser.bind(self))

	},

	fillBrowser: function(json){
		var self = this;

		var v = self.input.get('text');
		var previous_dir = self.getParentDir();

		if(previous_dir != v){
			self.back_button.set('data-value', previous_dir)
			self.back_button.set('html', '&laquo; '+self.getCurrentDirname(previous_dir))
			self.back_button.show()
		}
		else {
			self.back_button.hide()
		}

		if(self.use_cache)
			if(!json)
				json = self.cached[v];
			else
				self.cached[v] = json;

		setTimeout(function(){
			self.dir_list.empty();
			json.dirs.each(function(dir){
				if(dir.indexOf(v) != -1){
					new Element('li', {
						'data-value': dir,
						'text': self.getCurrentDirname(dir)
					}).inject(self.dir_list)
				}
			});
		}, 50);
	},

	getDirs: function(){
		var self = this;

		var c = self.input.get('text');

		if(self.cached[c] && self.use_cache){
			self.fillBrowser()
		}
		else {
			Api.request('directory.list', {
				'data': {
					'path': c,
					'show_hidden': +self.show_hidden.checked
				},
				'onComplete': self.fillBrowser.bind(self)
			})
		}
	},

	getParentDir: function(dir){
		var self = this;

		var v = dir || self.input.get('text');
		var sep = Api.getOption('path_sep');
		var dirs = v.split(sep);
			if(dirs.pop() == '')
				dirs.pop();

		return dirs.join(sep) + sep
	},

	getCurrentDirname: function(dir){
		var self = this;

		var dir_split = dir.split(Api.getOption('path_sep'));

		return dir_split[dir_split.length-2] || '/'
	},

	getValue: function(){
		var self = this;
		return self.input.get('text');
	}
});
