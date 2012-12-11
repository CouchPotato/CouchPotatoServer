Page.Settings = new Class({

	Extends: PageBase,

	name: 'settings',
	title: 'Change settings.',
	wizard_only: false,

	tabs: {},
	current: 'about',
	has_tab: false,

	initialize: function(options){
		var self = this;
		self.parent(options);

		// Add to more menu
		if(self.name == 'settings')
			App.getBlock('more').addLink(new Element('a', {
				'href': App.createUrl(self.name),
				'text': self.name.capitalize(),
				'title': self.title
			}), 'top')

	},

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
		var action = (action == 'index' ? 'about' : action) || self.action;

		if(self.current)
			self.toggleTab(self.current, true);

		var tab = self.toggleTab(action);
		self.current = tab == self.tabs.general ? 'general' : action;

	},

	toggleTab: function(tab_name, hide){
		var self = this;

		var a = hide ? 'removeClass' : 'addClass';
		var c = 'active';

		var t = self.tabs[tab_name] || self.tabs[self.action] || self.tabs.general;

		// Subtab
		var subtab = null
		Object.each(self.params, function(param, subtab_name){
			subtab = subtab_name;
		})

		self.el.getElements('li.'+c+' , .tab_content.'+c).each(function(active){
			active.removeClass(c);
		});

		if (t.subtabs[subtab]){
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
		self.el[c]('show_advanced');

		Cookie.write('advanced_toggle_checked', +self.advanced_toggle.checked, {'duration': 365});
	},

	create: function(json){
		var self = this;

		self.el.adopt(
			self.tabs_container = new Element('ul.tabs'),
			self.containers = new Element('form.uniForm.containers').adopt(
				new Element('label.advanced_toggle').adopt(
					new Element('span', {
						'text': 'Show advanced settings'
					}),
					self.advanced_toggle = new Element('input[type=checkbox].inlay', {
						'checked': +Cookie.read('advanced_toggle_checked'),
						'events': {
							'change': self.showAdvanced.bind(self)
						}
					})
				)
			)
		);
		self.showAdvanced();

		new Form.Check(self.advanced_toggle);

		// Add content to tabs
		var options = [];
		Object.each(json.options, function(section, section_name){
			section['section_name'] = section_name;
			options.include(section);
		})

		options.sort(function(a, b){
			return (a.order || 100) - (b.order || 100)
		}).each(function(section){
			var section_name = section.section_name;

			// Add groups to content
			section.groups.sortBy('order').each(function(group){
				if(group.hidden) return;

				if(self.wizard_only && !group.wizard)
					return;

				// Create tab
				if(!self.tabs[group.tab] || !self.tabs[group.tab].groups)
					self.createTab(group.tab, {});
				var content_container = self.tabs[group.tab].content

				// Create subtab
				if(group.subtab){
					if (!self.tabs[group.tab].subtabs[group.subtab])
						self.createSubTab(group.subtab, {}, self.tabs[group.tab], group.tab);
					var content_container = self.tabs[group.tab].subtabs[group.subtab].content
				}

				// Create the group
				if(!self.tabs[group.tab].groups[group.name]){
					var group_el = self.createGroup(group)
						.inject(content_container)
						.addClass('section_'+section_name);
					self.tabs[group.tab].groups[group.name] = group_el
				}

				// Add options to group
				group.options.sort(function(a, b){
					return (a.order || 100) - (b.order || 100)
				}).each(function(option){
					if(option.hidden) return;
					var class_name = (option.type || 'string').capitalize();
					var input = new Option[class_name](section_name, option.name, self.getValue(section_name, option.name), option);
						input.inject(self.tabs[group.tab].groups[group.name]);
						input.fireEvent('injected');
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

		var label = tab.label || (tab.name || tab_name).capitalize()
		var tab_el = new Element('li.t_'+tab_name).adopt(
			new Element('a', {
				'href': App.createUrl(self.name+'/'+tab_name),
				'text': label
			}).adopt()
		).inject(self.tabs_container);

		if(!self.tabs[tab_name])
			self.tabs[tab_name] = {
				'label': label
			}

		self.tabs[tab_name] = Object.merge(self.tabs[tab_name], {
			'tab': tab_el,
			'subtabs': {},
			'content': new Element('div.tab_content.tab_'+tab_name).inject(self.containers),
			'groups': {}
		})

		return self.tabs[tab_name]

	},

	createSubTab: function(tab_name, tab, parent_tab, parent_tab_name){
		var self = this;

		if(parent_tab.subtabs[tab_name])
			return parent_tab.subtabs[tab_name]

		if(!parent_tab.subtabs_el)
			parent_tab.subtabs_el = new Element('ul.subtabs').inject(parent_tab.tab);

		var label = tab.label || (tab.name || tab_name.replace('_', ' ')).capitalize()
		var tab_el = new Element('li.t_'+tab_name).adopt(
			new Element('a', {
				'href': App.createUrl(self.name+'/'+parent_tab_name+'/'+tab_name),
				'text': label
			}).adopt()
		).inject(parent_tab.subtabs_el);

		if(!parent_tab.subtabs[tab_name])
			parent_tab.subtabs[tab_name] = {
				'label': label
			}

		parent_tab.subtabs[tab_name] = Object.merge(parent_tab.subtabs[tab_name], {
			'tab': tab_el,
			'content': new Element('div.tab_content.tab_'+tab_name).inject(self.containers),
			'groups': {}
		});

		return parent_tab.subtabs[tab_name]

	},

	createGroup: function(group){
		var self = this;

		var group_el = new Element('fieldset', {
			'class': (group.advanced ? 'inlineLabels advanced' : 'inlineLabels') + ' group_' + (group.name || '') + ' subtab_' + (group.subtab || '')
		}).adopt(
			new Element('h2', {
				'text': group.label || (group.name).capitalize()
			}).adopt(
				new Element('span.hint', {
					'html': group.description || ''
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

	initialize: function(section, name, value, options){
		var self = this
		self.setOptions(options)

		self.section = section;
		self.name = name;
		self.value = self.previous_value = value;

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
			'text': (self.options.label || self.options.name.replace('_', ' ')).capitalize()
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
		return this.value;
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
				'value': self.getSettingValue(),
				'placeholder': self.getPlaceholder()
			})
		);
	},

	getPlaceholder: function(){
		return this.options.placeholder
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

		new Form.Check(self.input);

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

		self.input.addEvent('focus', function(){
			self.input.set('value', '')
		})

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
				'id': 'r-'+randomString()
			})
		);

		new Form.Check(self.input);
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

Option.Float = new Class({
	Extends: Option.Int
});

Option.Directory = new Class({

	Extends: OptionBase,

	type: 'span',
	browser: null,
	save_on_change: false,
	use_cache: false,

	create: function(){
		var self = this;

		self.el.adopt(
			self.createLabel(),
			self.directory_inlay = new Element('span.directory.inlay', {
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
						'click:relay(li:not(.empty))': function(e, el){
							(e).preventDefault();
							self.selectDirectory(el.get('data-value'))
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
								self.input.set('text', '');
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
								self.hideBrowser(e, true)
							}
						}
					})
				)
			).inject(self.directory_inlay, 'before');

			new Form.Check(self.show_hidden);
		}

		self.initial_directory = self.input.get('text');

		self.getDirs()
		self.browser.show()
		self.el.addEvent('outerClick', self.hideBrowser.bind(self))
	},

	hideBrowser: function(e, save){
		var self = this;
		(e).preventDefault();

		if(save)
			self.save()
		else
			self.input.set('text', self.initial_directory);

		self.browser.hide()
		self.el.removeEvents('outerClick')

	},

	fillBrowser: function(json){
		var self = this;

		self.data = json;

		var v = self.getValue();
		var previous_dir = self.getParentDir();

		if(v == '')
			self.input.set('text', json.home);

		if(previous_dir != v && previous_dir.length >= 1 && !json.is_root){

			var prev_dirname = self.getCurrentDirname(previous_dir);
			if(previous_dir == json.home)
				prev_dirname = 'Home';
			else if (previous_dir == '/' && json.platform == 'nt')
				prev_dirname = 'Computer';

			self.back_button.set('data-value', previous_dir)
			self.back_button.set('html', '&laquo; '+prev_dirname)
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

		self.dir_list.empty();
		if(json.dirs.length > 0)
			json.dirs.each(function(dir){
				new Element('li', {
					'data-value': dir,
					'text': self.getCurrentDirname(dir)
				}).inject(self.dir_list)
			});
		else
			new Element('li.empty', {
				'text': 'Selected folder is empty'
			}).inject(self.dir_list)
	},

	getDirs: function(){
		var self = this;

		var c = self.getValue();

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

		if(!dir && self.data && self.data.parent)
			return self.data.parent;

		var v = dir || self.getValue();
		var sep = Api.getOption('path_sep');
		var dirs = v.split(sep);
			if(dirs.pop() == '')
				dirs.pop();

		return dirs.join(sep) + sep
	},

	getCurrentDirname: function(dir){
		var self = this;

		var dir_split = dir.split(Api.getOption('path_sep'));

		return dir_split[dir_split.length-2] || Api.getOption('path_sep')
	},

	getValue: function(){
		var self = this;
		return self.input.get('text');
	}
});



Option.Directories = new Class({

	Extends: Option.String,

	directories: [],
	delimiter: '::',

	afterInject: function(){
		var self = this;

		self.el.setStyle('display', 'none');

		self.directories = [];
		self.getValue().split(self.delimiter).each(function(value){
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
		if(dirs.length == 0)
			$(dir).inject(parent)
		else
			$(dir).inject(dirs.getLast(), 'after');

		// Replace some properties
		dir.save = self.saveItems.bind(self);
		$(dir).getElement('label').set('text', 'Movie Folder');
		$(dir).getElement('.formHint').destroy();
		$(dir).addClass('multi_directory');

		if(!value)
			$(dir).addClass('is_empty');

		// Add remove button
		new Element('a.icon.delete', {
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

		var dirs = []
		self.directories.each(function(dir){
			if(dir.getValue()){
				$(dir).removeClass('is_empty');
				dirs.include(dir.getValue());
			}
			else
				$(dir).addClass('is_empty');
		});

		self.input.set('value', dirs.join(self.delimiter));
		self.input.fireEvent('change');

		self.addDirectory();

	}


});

Option.Choice = new Class({
	Extends: Option.String,

	afterInject: function(){
		var self = this;

		self.tags = [];
		self.replaceInput();

		self.select = new Element('select').adopt(
			new Element('option[text=Add option]')
		).inject(self.tag_input, 'after');

		var o = self.options.options;
		Object.each(o.choices, function(label, choice){
			new Element('option', {
				'text': label,
				'value': o.pre + choice + o.post
			}).inject(self.select);
		});

		self.select = new Form.Dropdown(self.select, {
			'onChange': self.addSelection.bind(self)
		});
	},

	replaceInput: function(){
		var self = this;
		self.initialized = self.initialized ? self.initialized+1 : 1;

		var value = self.getValue();
		var matches = value.match(/<([^>]*)>/g);

		self.tag_input = new Element('ul.inlay', {
			'events': {
				'click': function(e){
					if(e.target == self.tag_input){
						var input = self.tag_input.getElement('li:last-child input');
						input.fireEvent('focus');
						input.focus();
						input.setCaretPosition(input.get('value').length);
					}

					self.el.addEvent('outerClick', function(){
						self.reset();
						self.el.removeEvents('outerClick');
					})
				}
			}
		}).inject(self.input, 'after');
		self.el.addClass('tag_input');

		var mtches = []
		if(matches)
			matches.each(function(match, mnr){
				var pos = value.indexOf(match),
					msplit = [value.substr(0, pos), value.substr(pos, match.length), value.substr(pos+match.length)];

				msplit.each(function(matchsplit, snr){
					if(msplit.length-1 == snr){
						value = matchsplit;

						if(matches.length-1 == mnr)
							mtches.append([value]);

						return;
					}
					mtches.append([value == matchsplit ? match : matchsplit]);
				});
			});

		if(mtches.length == 0 && value != '')
			mtches.include(value);

		mtches.each(self.addTag.bind(self));

		self.addLastTag();

		// Sortable
		self.sortable = new Sortables(self.tag_input, {
			'revert': true,
			'handle': '',
			'opacity': 0.5,
			'onComplete': function(){
				self.setOrder();
				self.reset();
			}
		});

		// Calc width on show
		var input_group = self.tag_input.getParent('.tab_content');
		input_group.addEvent('activate', self.setAllWidth.bind(self));
	},

	addLastTag: function(){
		if(this.tag_input.getElement('li.choice:last-child') || !this.tag_input.getElement('li'))
			this.addTag('');
	},

	addTag: function(tag){
		var self = this;
		tag = new Option.Choice.Tag(tag, {
			'onChange': self.setOrder.bind(self),
			'onBlur': function(){
				self.addLastTag();
			},
			'onGoLeft': function(){
				self.goLeft(this)
			},
			'onGoRight': function(){
				self.goRight(this)
			}
		});
		$(tag).inject(self.tag_input);

		if(self.initialized > 1)
			tag.setWidth();
		else
			(function(){ tag.setWidth(); }).delay(10, self);

		self.tags.include(tag);

		return tag;
	},

	goLeft: function(from_tag){
		var self = this;

		from_tag.blur();

		var prev_index = self.tags.indexOf(from_tag)-1;
		if(prev_index >= 0)
			self.tags[prev_index].selectFrom('right')
		else
			from_tag.focus();

	},
	goRight: function(from_tag){
		var self = this;

		from_tag.blur();

		var next_index = self.tags.indexOf(from_tag)+1;
		if(next_index < self.tags.length)
			self.tags[next_index].selectFrom('left')
		else
			from_tag.focus();
	},

	setOrder: function(){
		var self = this;

		var value = '';
		self.tag_input.getElements('li').each(function(el){
			value += el.getElement('span').get('text');
		});
		self.addLastTag();

		self.input.set('value', value);
		self.input.fireEvent('change');
		self.setAllWidth();
	},

	addSelection: function(){
		var self = this;

		var tag = self.addTag(self.el.getElement('.selection input').get('value'));
		self.sortable.addItems($(tag));
		self.setOrder();
		self.setAllWidth();
	},

	reset: function(){
		var self = this;

		self.tag_input.destroy();
		self.sortable.detach();

		self.replaceInput();
		self.setAllWidth();
	},

	setAllWidth: function(){
		var self = this;
		self.tags.each(function(tag){
			tag.setWidth.delay(10, tag);
		});
	}

});

Option.Choice.Tag = new Class({

	Implements: [Options, Events],

	options: {
		'pre': '<',
		'post': '>'
	},

	initialize: function(tag, options){
		var self = this;
		self.setOptions(options);

		self.tag = tag;
		self.is_choice = tag.substr(0, 1) == self.options.pre && tag.substr(-1) == self.options.post;

		self.create();
	},

	create: function(){
		var self = this;

		self.el =  new Element('li', {
			'class': self.is_choice ? 'choice' : '',
			'styles': {
				'border': 0
			},
			'events': {
				'mouseover': !self.is_choice ? self.fireEvent.bind(self, 'focus') : function(){}
			}
		}).adopt(
			self.input = new Element(self.is_choice ? 'span' : 'input', {
				'text': self.tag,
				'value': self.tag,
				'styles': {
					'width': 0
				},
				'events': {
					'keyup': self.is_choice ? null : function(e){
						var current_caret_pos = self.input.getCaretPosition();
						if(e.key == 'left' && current_caret_pos == self.last_caret_pos){
							self.fireEvent('goLeft');
						}
						else if (e.key == 'right' && self.last_caret_pos === current_caret_pos){
							self.fireEvent('goRight');
						}
						self.last_caret_pos = self.input.getCaretPosition();

						self.setWidth();
						self.fireEvent('change');
					},
					'focus': self.fireEvent.bind(self, 'focus'),
					'blur': self.fireEvent.bind(self, 'blur')
				}
			}),
			self.span = !self.is_choice ? new Element('span', {
				'text': self.tag
			}) : null,
			self.del_button = new Element('a.delete', {
				'events': {
					'click': self.del.bind(self)
				}
			})
		);

		self.addEvent('focus', self.setWidth.bind(self));

	},

	blur: function(){
		var self = this;

		self.input.blur();

		self.selected = false;
		self.el.removeClass('selected');
		self.input.removeEvents('outerClick');
	},

	focus: function(){
		var self = this;
		if(!self.is_choice){
			this.input.focus();
		}
		else {
			if(self.selected) return;
			self.selected = true;
			self.el.addClass('selected');
			self.input.addEvent('outerClick', self.blur.bind(self));

			var temp_input = new Element('input', {
				'events': {
					'keydown': function(e){
						e.stop();

						if(e.key == 'right'){
							self.fireEvent('goRight');
							this.destroy();
						}
						else if (e.key == 'left'){
							self.fireEvent('goLeft');
							this.destroy();
						}
						else if (e.key == 'backspace'){
							self.del();
							this.destroy();
							self.fireEvent('goLeft');
						}
					}
				},
				'styles': {
					'height': 0,
					'width': 0,
					'position': 'absolute',
					'top': -200
				}
			});
			self.el.adopt(temp_input)
			temp_input.focus();
		}
	},

	selectFrom: function(direction){
		var self = this;

		if(!direction || self.is_choice){
			self.focus();
		}
		else {
			self.focus();
			var position = direction == 'left' ? 0 : self.input.get('value').length;
			self.input.setCaretPosition(position);
		}

	},

	setWidth: function(){
		var self = this;

		if(self.span && self.input){
			self.span.set('text', self.input.get('value'));
			self.input.setStyle('width', self.span.getSize().x+2);
		}
	},

	del: function(){
		var self = this;
		self.el.destroy();
		self.fireEvent('change');
	},

	getValue: function(){
		return this.span.get('text');
	},

	toElement: function(){
		return this.el;
	}

});

Option.Combined = new Class({

	Extends: Option.String,

	afterInject: function(){
		var self = this;

		self.fieldset = self.input.getParent('fieldset');
		self.combined_list = new Element('div.combined_table').inject(self.fieldset.getElement('h2'), 'after');
		self.values = {}
		self.inputs = {}
		self.items = []

		self.options.combine.each(function(name){

			self.inputs[name] = self.fieldset.getElement('input[name='+self.section+'['+name+']]');
			var values = self.inputs[name].get('value').split(',');

			values.each(function(value, nr){
				if (!self.values[nr]) self.values[nr] = {};
				self.values[nr][name] = value.trim();
			});

			self.inputs[name].getParent('.ctrlHolder').setStyle('display', 'none');
			self.inputs[name].addEvent('change', self.addEmpty.bind(self))

		});

		var head = new Element('div.head').inject(self.combined_list)

		Object.each(self.inputs, function(input, name){
			new Element('abbr', {
				'class': name,
				'text': input.getPrevious().get('text'),
				//'title': input.getNext().get('text')
			}).inject(head)
		})


		Object.each(self.values, function(item, nr){
			self.createItem(item);
		});

		self.addEmpty();

	},

	add_empty_timeout: 0,
	addEmpty: function(){
		var self = this;

		if(self.add_empty_timeout) clearTimeout(self.add_empty_timeout);

		var has_empty = 0;
		self.items.each(function(ctrl_holder){
			var empty_count = 0;
			self.options.combine.each(function(name){
				var input = ctrl_holder.getElement('input.'+name)
				if(input.get('value') == '' || input.get('type') == 'checkbox')
					empty_count++
			});
			has_empty += (empty_count == self.options.combine.length) ? 1 : 0;
			ctrl_holder[(empty_count == self.options.combine.length) ? 'addClass' : 'removeClass']('is_empty');
		});
		if(has_empty > 0) return;

		self.add_empty_timeout = setTimeout(function(){
			self.createItem(false, null);
		}, 10);
	},

	createItem: function(values){
		var self = this;

		var item = new Element('div.ctrlHolder').inject(self.combined_list),
			value_count = 0,
			value_empty = 0;

		self.options.combine.each(function(name){
			var value = values[name] || ''

			if(name.indexOf('use') != -1){
				var checkbox = new Element('input[type=checkbox].inlay.'+name, {
					'checked': +value,
					'events': {
						'click': self.saveCombined.bind(self),
						'change': self.saveCombined.bind(self)
					}
				}).inject(item);

				new Form.Check(checkbox);
			}
			else {
				value_count++;
				new Element('input[type=text].inlay.'+name, {
					'value': value,
					'placeholder': name,
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

		new Element('a.icon.delete', {
			'events': {
				'click': self.deleteCombinedItem.bind(self)
			}
		}).inject(item)

		self.items.include(item);


	},

	saveCombined: function(){
		var self = this;


		var temp = {}
		self.items.each(function(item, nr){
			self.options.combine.each(function(name){
				var input = item.getElement('input.'+name);
				if(item.hasClass('is_empty')) return;

				if(!temp[name]) temp[name] = [];
				temp[name][nr] = input.get('type') == 'checkbox' ? +input.get('checked') : input.get('value').trim();

			})
		});

		self.options.combine.each(function(name){
			self.inputs[name].set('value', (temp[name] || []).join(','));
			self.inputs[name].fireEvent('change');
		});

		self.addEmpty()

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