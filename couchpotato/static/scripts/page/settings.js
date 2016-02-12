Page.Settings = new Class({

	Extends: PageBase,

	order: 50,
	name: 'settings',
	title: 'Change settings.',
	wizard_only: false,

	tabs: {},
	lists: {},
	current: 'about',
	has_tab: false,

	open: function(action, params){
		var self = this;
		self.action = action == 'index' ? self.default_action : action;
		self.params = params;

		if(!self.data)
			self.getData(self.create.bind(self));
		else {
			self.openTab(action);
		}

		App.getBlock('navigation').activate(self.name);
	},

	openTab: function(action){
		var self = this;
		action = (action == 'index' ? 'about' : action) || self.action;

		if(self.current)
			self.toggleTab(self.current, true);

		var tab = self.toggleTab(action);
		self.current = tab == self.tabs.general ? 'general' : action;

	},

	toggleTab: function(tab_name, hide){
		var self = this;

		var a = hide ? 'removeClass' : 'addClass';
		var c = 'active';

		tab_name = tab_name.split('/')[0];
		var t = self.tabs[tab_name] || self.tabs[self.action] || self.tabs.general;

		// Subtab
		var subtab = null;
		Object.each(self.params, function(param, subtab_name){
			subtab = param;
		});

		self.content.getElements('li.'+c+' , .tab_content.'+c).each(function(active){
			active.removeClass(c);
		});

		if(t.subtabs[subtab]){
			t.tab[a](c);
			t.subtabs[subtab].tab[a](c);
			t.subtabs[subtab].content[a](c);

			if(!hide)
				t.subtabs[subtab].content.fireEvent('activate');
		}
		else {
			t.tab[a](c);
			t.content[a](c);

			if(!hide)
				t.content.fireEvent('activate');
		}

		return t;
	},

	getData: function(onComplete){
		var self = this;

		if(onComplete)
			Api.request('settings', {
				'useSpinner': true,
				'spinnerOptions': {
					'target': self.content
				},
				'onComplete': function(json){
					self.data = json;
					onComplete(json);
				}
			});

		return self.data;
	},

	getValue: function(section, name){
		var self = this;
		try {
			return self.data.values[section][name];
		}
		catch(e){
			return '';
		}
	},

	showAdvanced: function(){
		var self = this;

		var c = self.advanced_toggle.checked ? 'addClass' : 'removeClass';
		self.el[c]('show_advanced');

		Cookie.write('advanced_toggle_checked', +self.advanced_toggle.checked, {'duration': 365});
	},

	sortByOrder: function(a, b){
		return (a.order || 100) - (b.order || 100);
	},

	create: function(json){
		var self = this;

		self.navigation = new Element('div.navigation').adopt(
			new Element('h2[text=Settings]'),
			new Element('div.advanced_toggle').adopt(
				new Element('span', {
					'text': 'Show advanced'
				}),
				new Element('label.switch').adopt(
					self.advanced_toggle = new Element('input[type=checkbox]', {
						'checked': +Cookie.read('advanced_toggle_checked'),
						'events': {
							'change': self.showAdvanced.bind(self)
						}
					}),
					new Element('div.toggle')
				)
			)
		);

		self.tabs_container = new Element('ul.tabs');

		self.containers = new Element('form.uniForm.containers', {
			'events': {
				'click:relay(.enabler.disabled h2)': function(e, el){
					el.getPrevious().getElements('.check').fireEvent('click');
				}
			}
		});
		self.showAdvanced();

		// Add content to tabs
		var options = [];
		Object.each(json.options, function(section, section_name){
			section.section_name = section_name;
			options.include(section);
		});

		options.stableSort(self.sortByOrder).each(function(section){
			var section_name = section.section_name;

			// Add groups to content
			section.groups.stableSort(self.sortByOrder).each(function(group){
				if(group.hidden) return;

				if(self.wizard_only && !group.wizard)
					return;

				// Create tab
				if(!self.tabs[group.tab] || !self.tabs[group.tab].groups)
					self.createTab(group.tab, {});
				var content_container = self.tabs[group.tab].content;

				// Create subtab
				if(group.subtab){
					if(!self.tabs[group.tab].subtabs[group.subtab])
						self.createSubTab(group.subtab, group, self.tabs[group.tab], group.tab);
					content_container = self.tabs[group.tab].subtabs[group.subtab].content;
				}

				if(group.list && !self.lists[group.list]){
					self.lists[group.list] = self.createList(content_container);
				}

				// Create the group
				if(!self.tabs[group.tab].groups[group.name])
					self.tabs[group.tab].groups[group.name] = self.createGroup(group)
						.inject(group.list ? self.lists[group.list] : content_container)
						.addClass('section_'+section_name);

				// Create list if needed
				if(group.type && group.type == 'list'){
					if(!self.lists[group.name])
						self.lists[group.name] = self.createList(content_container);
					else
						self.lists[group.name].inject(self.tabs[group.tab].groups[group.name]);
				}

				// Add options to group
				group.options.stableSort(self.sortByOrder).each(function(option){
					if(option.hidden) return;
					var class_name = (option.type || 'string').capitalize();
					var input = new Option[class_name](section_name, option.name, self.getValue(section_name, option.name), option);
						input.inject(self.tabs[group.tab].groups[group.name]);
						input.fireEvent('injected');
				});

			});
		});

		requestTimeout(function(){
			self.el.grab(
				self.navigation
			);

			self.content.adopt(
				self.tabs_container,
				self.containers
			);

			self.fireEvent('create');
			self.openTab();
		}, 0);

	},

	createTab: function(tab_name, tab){
		var self = this;

		if(self.tabs[tab_name] && self.tabs[tab_name].tab)
			return self.tabs[tab_name].tab;

		var label = tab.label || (tab.name || tab_name).capitalize();
		var tab_el = new Element('li.t_'+tab_name).adopt(
			new Element('a', {
				'href': App.createUrl(self.name+'/'+tab_name),
				'text': label
			}).adopt()
		).inject(self.tabs_container);

		if(!self.tabs[tab_name])
			self.tabs[tab_name] = {
				'label': label
			};

		self.tabs[tab_name] = Object.merge(self.tabs[tab_name], {
			'tab': tab_el,
			'subtabs': {},
			'content': new Element('div.tab_content.tab_' + tab_name).inject(self.containers),
			'groups': {}
		});

		return self.tabs[tab_name];

	},

	createSubTab: function(tab_name, tab, parent_tab, parent_tab_name){
		var self = this;

		if(parent_tab.subtabs[tab_name])
			return parent_tab.subtabs[tab_name];

		if(!parent_tab.subtabs_el)
			parent_tab.subtabs_el = new Element('ul.subtabs').inject(parent_tab.tab);

		var label = tab.subtab_label || tab_name.replace('_', ' ').capitalize();
		var tab_el = new Element('li.t_'+tab_name).adopt(
			new Element('a', {
				'href': App.createUrl(self.name+'/'+parent_tab_name+'/'+tab_name),
				'text': label
			}).adopt()
		).inject(parent_tab.subtabs_el);

		if(!parent_tab.subtabs[tab_name])
			parent_tab.subtabs[tab_name] = {
				'label': label
			};

		parent_tab.subtabs[tab_name] = Object.merge(parent_tab.subtabs[tab_name], {
			'tab': tab_el,
			'content': new Element('div.tab_content.tab_'+tab_name).inject(self.containers),
			'groups': {}
		});

		return parent_tab.subtabs[tab_name];

	},

	createGroup: function(group){
		var hint;

		if((typeOf(group.description) == 'array')){
			hint = new Element('span.hint.more_hint', {
				'html': group.description[0]
			});

			createTooltip(group.description[1]).inject(hint);
		}
		else {
			hint = new Element('span.hint', {
				'html': group.description || ''
			});
		}

		var icon;
		if(group.icon){
			icon = new Element('span.icon').grab(new Element('img', {
				'src': 'data:image/png;base64,' + group.icon
			}));
		}

		var label = new Element('span.group_label', {
			'text': group.label || (group.name).capitalize()
		});

		return new Element('fieldset', {
			'class': (group.advanced ? 'inlineLabels advanced' : 'inlineLabels') + ' group_' + (group.name || '') + ' subtab_' + (group.subtab || '')
		}).grab(
			new Element('h2').adopt(icon, label, hint)
		);

	},

	createList: function(content_container){
		return new Element('div.option_list').inject(content_container);
	}

});

var OptionBase = new Class({

	Implements: [Options, Events],

	klass: '',
	focused_class: 'focused',
	save_on_change: true,
	read_only: false,

	initialize: function(section, name, value, options){
		var self = this;
		self.setOptions(options);

		self.section = section;
		self.name = name;
		self.value = self.previous_value = value;
		self.read_only = !(options && !options.readonly);

		self.createBase();
		self.create();
		self.createHint();
		self.setAdvanced();

		// Add focus events
		self.input.addEvents({
			'change': self.changed.bind(self),
			'keyup': self.changed.bind(self)
		});

		self.addEvent('injected', self.afterInject.bind(self));

	},

	/**
	 * Create the element
	 */
	createBase: function(){
		var self = this;
		self.el = new Element('div.ctrlHolder.' +
			self.section + '_' + self.name +
			(self.klass ? '.' + self.klass : '') +
			(self.read_only ? '.read_only' : '')
		);
	},

	create: function(){
	},

	createLabel: function(){
		var self = this;
		return new Element('label', {
			'text': (self.options.label || self.options.name.replace('_', ' ')).capitalize()
		});
	},

	setAdvanced: function(){
		this.el.addClass(this.options.advanced ? 'advanced' : '');
	},

	createHint: function(){
		var self = this;
		if(self.options.description){

			if((typeOf(self.options.description) == 'array')){
				var hint = new Element('p.formHint.more_hint', {
					'html': self.options.description[0]
				}).inject(self.el);

				createTooltip(self.options.description[1]).inject(hint);
			}
			else {
				new Element('p.formHint', {
					'html': self.options.description || ''
				}).inject(self.el);
			}
		}
	},

	afterInject: function(){
	},

	// Element has changed, do something
	changed: function(){
		var self = this;

		if(self.getValue() != self.previous_value){
			if(self.save_on_change){
				if(self.changed_timer) clearRequestTimeout(self.changed_timer);
				self.changed_timer = requestTimeout(self.save.bind(self), 300);
			}
			self.fireEvent('change');
		}

	},

	save: function(){
		var self = this,
			value = self.getValue(),
			ro = self.read_only;

		if (ro) {
			console.warn('Unable to save readonly-option ' + self.section + '.' + self.name);
			return;
		}

		App.fireEvent('setting.save.'+self.section+'.'+self.name, value);

		Api.request('settings.save', {
			'data': {
				'section': self.section,
				'name': self.name,
				'value': value
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

		requestTimeout(function(){
			self.el.removeClass(sc);
		}, 3000);
	},

	setName: function(name){
		this.name = name;
	},

	postName: function(){
		var self = this;
		return self.section + '[' + self.name + ']';
	},

	getValue: function(){
		var self = this;
		return self.input.get('value');
	},

	getSettingValue: function(){
		return this.value;
	},

	inject: function(el, position){
		this.el.inject(el, position);
		return this.el;
	},

	toElement: function(){
		return this.el;
	}
});

var Option = {};
Option.String = new Class({
	Extends: OptionBase,

	type: 'string',

	create: function(){
		var self = this;

		if(self.read_only){
			self.input = new Element('span', {
				'text': self.getSettingValue()
			});
		}
		else {
			self.input = new Element('input', {
				'type': 'text',
				'name': self.postName(),
				'value': self.getSettingValue(),
				'placeholder': self.getPlaceholder()
			});
		}

		self.el.adopt(
			self.createLabel(),
			self.input
		);
	},

	getPlaceholder: function(){
		return this.options.placeholder;
	}
});

Option.Dropdown = new Class({
	Extends: OptionBase,

	create: function(){
		var self = this;

		self.el.adopt(
			self.createLabel(),
			new Element('div.select_wrapper.icon-dropdown').grab(
				self.input = new Element('select', {
					'name': self.postName(),
					'readonly' : self.read_only,
					'disabled' : self.read_only
				})
			)
		);

		Object.each(self.options.values, function(value){
			new Element('option', {
				'text': value[0],
				'value': value[1]
			}).inject(self.input);
		});

		self.input.set('value', self.getSettingValue());
	}
});

Option.Checkbox = new Class({
	Extends: OptionBase,

	type: 'checkbox',

	create: function(){
		var self = this;

		var randomId = 'r-' + randomString();

		self.el.adopt(
			self.createLabel().set('for', randomId),
			self.input = new Element('input', {
				'name': self.postName(),
				'type': 'checkbox',
				'checked': self.getSettingValue(),
				'id': randomId,
				'readonly' : self.read_only,
				'disabled' : self.read_only
			})
		);

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

		self.el.adopt(
			self.createLabel(),
			self.input = new Element('input', {
				'type': 'text',
				'name': self.postName(),
				'value': self.getSettingValue() ? '********' : '',
				'placeholder': self.getPlaceholder(),
				'readonly' : self.read_only,
				'disabled' : self.read_only
			})
		);

		self.input.addEvent('focus', function(){
			self.input.set('value', '');
			self.input.set('type', 'password');
		});

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
			new Element('label.switch').adopt(
				self.input = new Element('input', {
					'type': 'checkbox',
					'checked': self.getSettingValue(),
					'id': 'r-'+randomString(),
					'readonly' : self.read_only,
					'disabled' : self.read_only,
				}),
				new Element('div.toggle')
			)
		);

	},

	changed: function(){
		this.parent();
		this.checkState();
	},

	checkState: function(){
		var self = this,
			enabled = self.getValue();

		self.parentFieldset[ enabled ? 'removeClass' : 'addClass']('disabled');

		//if(self.parentList)
		//	self.parentFieldset.inject(self.parentList.getElement('h3'), enabled ? 'before' : 'after');

	},

	afterInject: function(){
		var self = this;

		self.parentFieldset = self.el.getParent('fieldset').addClass('enabler');
		self.parentList = self.parentFieldset.getParent('.option_list');
		self.el.inject(self.parentFieldset, 'top');
		self.checkState();
	}

});

Option.Int = new Class({
	Extends: Option.String
});

Option.Float = new Class({
	Extends: Option.Int
});

Option.Directory = new Class({

	Extends: OptionBase,

	type: 'span',
	browser: null,
	save_on_change: false,
	use_cache: false,
	current_dir: '',

	create: function(){
		var self = this;
		if (self.read_only) {
			// create disabled textbox:
			self.el.adopt(
				self.createLabel(),
				self.input = new Element('input', {
					'type': 'text',
					'name': self.postName(),
					'value': self.getSettingValue(),
					'readonly' : true,
					'disabled' : true
				})
			);
		} else {
			self.el.adopt(
				self.createLabel(),
				self.directory_inlay = new Element('span.directory', {
					'events': {
						'click': self.showBrowser.bind(self)
					}
				}).adopt(
					self.input = new Element('input', {
						'value': self.getSettingValue(),
						'readonly' : self.read_only,
						'disabled' : self.read_only,
						'events': {
							'change': self.filterDirectory.bind(self),
							'keydown': function(e){
								if(e.key == 'enter' || e.key == 'tab')
									(e).stop();
							},
							'keyup': self.filterDirectory.bind(self),
							'paste': self.filterDirectory.bind(self)
						}
					})
				)
			);
		}

		self.cached = {};
	},

	filterDirectory: function(e){
		var self = this,
			value = self.getValue(),
			path_sep = Api.getOption('path_sep'),
			active_selector = 'li:not(.blur):not(.empty)',
			first;

		if(e.key == 'enter' || e.key == 'tab'){
			(e).stop();

			first = self.dir_list.getElement(active_selector);
			if(first){
				self.selectDirectory(first.get('data-value'));
			}
		}
		else {

			// New folder
			if(value.substr(-1) == path_sep){
				if(self.current_dir != value)
					self.selectDirectory(value);
			}
			else {
				var pd = self.getParentDir(value);
				if(self.current_dir != pd)
					self.getDirs(pd);

				var folder_filter = value.split(path_sep).getLast();
				self.dir_list.getElements('li').each(function(li){
					var valid = li.get('text').substr(0, folder_filter.length).toLowerCase() != folder_filter.toLowerCase();
					li[valid ? 'addClass' : 'removeClass']('blur');
				});

				first = self.dir_list.getElement(active_selector);
				if(first){
					if(!self.dir_list_scroll)
						self.dir_list_scroll = new Fx.Scroll(self.dir_list, {
							'transition': 'quint:in:out'
						});

					self.dir_list_scroll.toElement(first);
				}
			}
		}
	},

	selectDirectory: function(dir){
		var self = this;

		self.input.set('value', dir);

		self.getDirs();
	},

	previousDirectory: function(){
		var self = this;

		self.selectDirectory(self.getParentDir());
	},

	caretAtEnd: function(){
		var self = this;

		self.input.focus();

		if (typeof self.input.selectionStart == "number") {
			self.input.selectionStart = self.input.selectionEnd = self.input.get('value').length;
		} else if (typeof el.createTextRange != "undefined") {
			self.input.focus();
			var range = self.input.createTextRange();
			range.collapse(false);
			range.select();
		}
	},

	showBrowser: function(){
		var self = this;

		// Move caret to back of the input
		if(!self.browser || self.browser && !self.browser.isVisible())
			self.caretAtEnd();

		if(!self.browser){
			self.browser = new Element('div.directory_list').adopt(
				self.pointer = new Element('div.pointer'),
				new Element('div.wrapper').adopt(
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
							self.show_hidden = new Element('input[type=checkbox]', {
								'events': {
									'change': function(){
										self.getDirs();
									}
								}
							})
						)
					),
					self.dir_list = new Element('ul', {
						'events': {
							'click:relay(li:not(.empty))': function(e, el){
								(e).preventDefault();
								self.selectDirectory(el.get('data-value'));
							},
							'mousewheel': function(e){
								(e).stopPropagation();
							}
						}
					}),
					new Element('div.actions').adopt(
						new Element('a.clear.button', {
							'text': 'Clear',
							'events': {
								'click': function(e){
									self.input.set('value', '');
									self.hideBrowser(e, true);
								}
							}
						}),
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
									self.hideBrowser(e, true);
								}
							}
						})
					)
				)
			).inject(self.directory_inlay, 'before');
		}

		self.initial_directory = self.input.get('value');

		self.getDirs();
		self.browser.show();
		self.el.addEvent('outerClick', self.hideBrowser.bind(self));
	},

	hideBrowser: function(e, save){
		var self = this;
		(e).preventDefault();

		if(save)
			self.save();
		else
			self.input.set('value', self.initial_directory);

		self.browser.hide();
		self.el.removeEvents('outerClick');

	},

	fillBrowser: function(json){
		var self = this,
			v = self.getValue();

		self.data = json;

		var previous_dir = json.parent;

		if(v === '')
			self.input.set('value', json.home);

		if(previous_dir.length >= 1 && !json.is_root){

			var prev_dirname = self.getCurrentDirname(previous_dir);
			if(previous_dir == json.home)
				prev_dirname = 'Home Folder';
			else if(previous_dir == '/' && json.platform == 'nt')
				prev_dirname = 'Computer';

			self.back_button.set('data-value', previous_dir);
			self.back_button.set('html', '&laquo; ' + prev_dirname);
			self.back_button.show();
		}
		else {
			self.back_button.hide();
		}

		if(self.use_cache)
			if(!json)
				json = self.cached[v];
			else
				self.cached[v] = json;

		self.dir_list.empty();
		if(json.dirs.length > 0)
			json.dirs.each(function(dir){
				new Element('li', {
					'data-value': dir,
					'text': self.getCurrentDirname(dir)
				}).inject(self.dir_list);
			});
		else
			new Element('li.empty', {
				'text': 'Selected folder is empty'
			}).inject(self.dir_list);

		//fix for webkit type browsers to refresh the dom for the file browser
		//http://stackoverflow.com/questions/3485365/how-can-i-force-webkit-to-redraw-repaint-to-propagate-style-changes
		self.dir_list.setStyle('webkitTransform', 'scale(1)');
		self.caretAtEnd();
	},

	getDirs: function(dir){
		var self = this,
			c = dir || self.getValue();

		if(self.cached[c] && self.use_cache){
			self.fillBrowser();
		}
		else {
			Api.request('directory.list', {
				'data': {
					'path': c,
					'show_hidden': +self.show_hidden.checked
				},
				'onComplete': function(json){
					self.current_dir = c;
					self.fillBrowser(json);
				}
			});
		}
	},

	getParentDir: function(dir){
		var self = this;

		if(!dir && self.data && self.data.parent)
			return self.data.parent;

		var v = dir || self.getValue();
		var sep = Api.getOption('path_sep');
		var dirs = v.split(sep);
		if(dirs.pop() === '')
			dirs.pop();

		return dirs.join(sep) + sep;
	},

	getCurrentDirname: function(dir){
		var dir_split = dir.split(Api.getOption('path_sep'));

		return dir_split[dir_split.length-2] || Api.getOption('path_sep');
	},

	getValue: function(){
		var self = this;
		return self.input.get('value');
	}
});



Option.Directories = new Class({

	Extends: Option.String,

	directories: [],

	afterInject: function(){
		var self = this;

		self.el.setStyle('display', 'none');

		self.directories = [];

		self.getSettingValue().each(function(value){
			self.addDirectory(value);
		});

		self.addDirectory();

	},

	addDirectory: function(value){
		var self = this;

		var has_empty = false;
		self.directories.each(function(dir){
			if(!dir.getValue())
				has_empty = true;
		});
		if(has_empty) return;

		var dir = new Option.Directory(self.section, self.name, value || '', self.options);

		var parent = self.el.getParent('fieldset');
		var dirs = parent.getElements('.multi_directory');
		if(dirs.length === 0)
			$(dir).inject(parent);
		else
			$(dir).inject(dirs.getLast(), 'after');

		// TODO : Replace some properties
		dir.save = self.saveItems.bind(self);
		$(dir).getElement('label').set('text', 'Movie Folder');
		$(dir).getElement('.formHint').destroy();
		$(dir).addClass('multi_directory');

		if(!value)
			$(dir).addClass('is_empty');

		// Add remove button
		new Element('a.icon-delete.delete', {
			'events': {
				'click': self.delItem.bind(self, dir)
			}
		}).inject(dir);

		self.directories.include(dir);

	},

	delItem: function(dir){
		var self = this;
		self.directories.erase(dir);

		$(dir).destroy();

		self.saveItems();
		self.addDirectory();
	},

	saveItems: function(){
		var self = this;

		var dirs = [];
		self.directories.each(function(dir){
			if(dir.getValue()){
				$(dir).removeClass('is_empty');
				dirs.include(dir.getValue());
			}
			else
				$(dir).addClass('is_empty');
		});

		self.input.set('value', JSON.encode(dirs) );
		self.input.fireEvent('change');

		self.addDirectory();

	}
});

Option.Choice = new Class({
	Extends: Option.String,
	klass: 'choice',

	afterInject: function(){
		var self = this;

		var wrapper = new Element('div.select_wrapper.icon-dropdown').grab(
			self.select = new Element('select.select', {
				'events': {
					'change': self.addSelection.bind(self)
				}
			}).grab(
				new Element('option[text=Add option]')
			)
		);

		var o = self.options.options;
		Object.each(o.choices, function(label, choice){
			new Element('option', {
				'text': label,
				'value': o.pre + choice + o.post
			}).inject(self.select);
		});

		wrapper.inject(self.input, 'after');

	},

	addSelection: function(){
		var self = this;
		self.input.set('value', self.input.get('value') + self.select.get('value'));
		self.input.fireEvent('change');
	}

});

Option.Combined = new Class({

	Extends: Option.String,

	afterInject: function(){
		var self = this;

		self.fieldset = self.input.getParent('fieldset');
		self.combined_list = new Element('div.combined_table').inject(self.fieldset.getElement('h2'), 'after');
		self.values = {};
		self.inputs = {};
		self.items = [];
		self.labels = {};
		self.descriptions = {};

		self.options.combine.each(function(name){

			self.inputs[name] = self.fieldset.getElement('input[name='+self.section+'['+name+']]');
			var values = self.inputs[name].get('value').split(',');

			values.each(function(value, nr){
				if(!self.values[nr]) self.values[nr] = {};
				self.values[nr][name] = value.trim();
			});

			self.inputs[name].getParent('.ctrlHolder').setStyle('display', 'none');
			self.inputs[name].addEvent('change', self.addEmpty.bind(self));

		});

		var head = new Element('div.head').inject(self.combined_list);

		Object.each(self.inputs, function(input, name){
			var _in = input.getNext();
			self.labels[name] = input.getPrevious().get('text');
			self.descriptions[name] = _in ? _in.get('text') : '';

			new Element('abbr', {
				'class': name,
				'text': self.labels[name],
				'title': self.descriptions[name]
			}).inject(head);
		});


		Object.each(self.values, function(item){
			self.createItem(item);
		});

		self.addEmpty();

	},

	add_empty_timeout: 0,
	addEmpty: function(){
		var self = this;

		if(self.add_empty_timeout) clearRequestTimeout(self.add_empty_timeout);

		var has_empty = 0;
		self.items.each(function(ctrl_holder){
			var empty_count = 0;
			self.options.combine.each(function(name){
				var input = ctrl_holder.getElement('input.' + name);
				if(input.get('value') === '' || input.get('type') == 'checkbox')
					empty_count++;
			});
			has_empty += (empty_count == self.options.combine.length) ? 1 : 0;
			ctrl_holder[(empty_count == self.options.combine.length) ? 'addClass' : 'removeClass']('is_empty');
		});
		if(has_empty > 0) return;

		self.add_empty_timeout = requestTimeout(function(){
			self.createItem({'use': true});
		}, 10);
	},

	createItem: function(values){
		var self = this;

		var item = new Element('div.ctrlHolder').inject(self.combined_list),
			value_count = 0,
			value_empty = 0;

		self.options.combine.each(function(name){
			var value = values[name] || '';

			if(name.indexOf('use') != -1){
				var checkbox = new Element('input[type=checkbox].'+name, {
					'checked': +value,
					'events': {
						'click': self.saveCombined.bind(self),
						'change': self.saveCombined.bind(self)
					}
				}).inject(item);
			}
			else {
				value_count++;
				new Element('input[type=text].'+name, {
					'value': value,
					'placeholder': self.labels[name] || name,
					'events': {
						'keyup': self.saveCombined.bind(self),
						'change': self.saveCombined.bind(self)
					}
				}).inject(item);

				if(!value)
					value_empty++;
			}


		});

		item[value_empty == value_count ? 'addClass' : 'removeClass']('is_empty');

		new Element('a.icon-cancel.delete', {
			'events': {
				'click': self.deleteCombinedItem.bind(self)
			}
		}).inject(item);

		self.items.include(item);


	},

	saveCombined: function(){
		var self = this,
			temp = {};

		self.items.each(function(item, nr){
			self.options.combine.each(function(name){
				var input = item.getElement('input.'+name);
				if(item.hasClass('is_empty')) return;

				if(!temp[name]) temp[name] = [];
				temp[name][nr] = input.get('type') == 'checkbox' ? +input.get('checked') : input.get('value').trim();

			});
		});

		self.options.combine.each(function(name){
			self.inputs[name].set('value', (temp[name] || []).join(','));
			self.inputs[name].fireEvent('change');
		});

		self.addEmpty();

	},

	deleteCombinedItem: function(e){
		var self = this;
		(e).preventDefault();

		var item = e.target.getParent();

		self.items.erase(item);
		item.destroy();

		self.saveCombined();
	}

});

var createTooltip = function(description){

	var tip = new Element('div.tooltip', {
			'events': {
				'mouseenter': function(){
					tip.addClass('shown');
				},
				'mouseleave': function(){
					tip.removeClass('shown');
				}
			}
		}).adopt(
			new Element('a.icon-info.info'),
			new Element('div.tip', {
				'html': description
			})
		);

	return tip;
};
