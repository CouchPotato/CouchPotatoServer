var CategoryListBase = new Class({

	initialize: function(){
		var self = this;

		App.addEvent('loadSettings', self.addSettings.bind(self));
	},

	setup: function(categories){
		var self = this;

		self.categories = [];
		Array.each(categories, self.createCategory.bind(self));

	},

	addSettings: function(){
		var self = this;

		self.settings = App.getPage('Settings');
		self.settings.addEvent('create', function(){
			var tab = self.settings.createSubTab('category', {
				'label': 'Categories',
				'name': 'category',
				'subtab_label': 'Category & filtering'
			}, self.settings.tabs.searcher ,'searcher');

			self.tab = tab.tab;
			self.content = tab.content;

			self.createList();
			self.createOrdering();

		});

		// Add categories in renamer
		self.settings.addEvent('create', function(){
			var renamer_group = self.settings.tabs.renamer.groups.renamer;

			self.categories.each(function(category){

				var input = new Option.Directory('section_name', 'option.name', category.get('destination'), {
					'name': category.get('label')
				});
					input.inject(renamer_group.getElement('.renamer_to'));
					input.fireEvent('injected');

					input.save = function(){
						category.data.destination = input.getValue();
						category.save();
					};

			});

		})

	},

	createList: function(){
		var self = this;

		var count = self.categories.length;

		self.settings.createGroup({
			'label': 'Categories',
			'description': 'Create categories, each one extending global filters. (Needs refresh \'' +(App.isMac() ? 'CMD+R' : 'F5')+ '\' after editing)'
		}).inject(self.content).adopt(
			self.category_container = new Element('div.container'),
			new Element('a.add_new_category', {
				'text': count > 0 ? 'Create another category' : 'Click here to create a category.',
				'events': {
					'click': function(){
						var category = self.createCategory();
						$(category).inject(self.category_container)
					}
				}
			})
		);

		// Add categories, that aren't part of the core (for editing)
		Array.each(self.categories, function(category){
			$(category).inject(self.category_container)
		});

	},

	getCategory: function(id){
		return this.categories.filter(function(category){
			return category.data._id == id
		}).pick()
	},

	getAll: function(){
		return this.categories;
	},

	createCategory: function(data){
		var self = this;

		var data = data || {'id': randomString()};
		var category = new Category(data);
		self.categories.include(category);

		return category;
	},

	createOrdering: function(){
		var self = this;

		var category_list;
		self.settings.createGroup({
			'label': 'Category ordering'
		}).adopt(
			new Element('.ctrlHolder#category_ordering').adopt(
				new Element('label[text=Order]'),
				category_list = new Element('ul'),
				new Element('p.formHint', {
					'html': 'Change the order the categories are in the dropdown list.<br />First one will be default.'
				})
			)
		).inject(self.content);

		Array.each(self.categories, function(category){
			new Element('li', {'data-id': category.data._id}).adopt(
				new Element('span.category_label', {
					'text': category.data.label
				}),
				new Element('span.handle')
			).inject(category_list);

		});

		// Sortable
		self.category_sortable = new Sortables(category_list, {
			'revert': true,
			'handle': '',
			'opacity': 0.5,
			'onComplete': self.saveOrdering.bind(self)
		});

	},

	saveOrdering: function(){
		var self = this;

		var ids = [];

		self.category_sortable.list.getElements('li').each(function(el){
			ids.include(el.get('data-id'));
		});

		Api.request('category.save_order', {
			'data': {
				'ids': ids
			}
		});

	}

});

window.CategoryList = new CategoryListBase();

var Category = new Class({

	data: {},

	initialize: function(data){
		var self = this;

		self.data = data;

		self.create();

		self.el.addEvents({
			'change:relay(select)': self.save.bind(self, 0),
			'keyup:relay(input[type=text])': self.save.bind(self, [300])
		});

	},

	create: function(){
		var self = this;

		var data = self.data;

		self.el = new Element('div.category').adopt(
			self.delete_button = new Element('span.delete.icon2', {
				'events': {
					'click': self.del.bind(self)
				}
			}),
			new Element('.category_label.ctrlHolder').adopt(
				new Element('label', {'text':'Name'}),
				new Element('input.inlay', {
					'type':'text',
					'value': data.label,
					'placeholder': 'Example: Kids, Horror or His'
				}),
				new Element('p.formHint', {'text': 'See global filters for explanation.'})
			),
			new Element('.category_preferred.ctrlHolder').adopt(
				new Element('label', {'text':'Preferred'}),
				new Element('input.inlay', {
					'type':'text',
					'value': data.preferred,
					'placeholder': 'Blu-ray, DTS'
				})
			),
			new Element('.category_required.ctrlHolder').adopt(
				new Element('label', {'text':'Required'}),
				new Element('input.inlay', {
					'type':'text',
					'value': data.required,
					'placeholder': 'Example: DTS, AC3 & English'
				})
			),
			new Element('.category_ignored.ctrlHolder').adopt(
				new Element('label', {'text':'Ignored'}),
				new Element('input.inlay', {
					'type':'text',
					'value': data.ignored,
					'placeholder': 'Example: dubbed, swesub, french'
				})
			)
		);

		self.makeSortable()

	},

	save: function(delay){
		var self = this;

		if(self.save_timer) clearTimeout(self.save_timer);
		self.save_timer = (function(){

			Api.request('category.save', {
				'data': self.getData(),
				'useSpinner': true,
				'spinnerOptions': {
					'target': self.el
				},
				'onComplete': function(json){
					if(json.success){
						self.data = json.category;
					}
				}
			});

		}).delay(delay || 0, self)

	},

	getData: function(){
		var self = this;

		return {
			'id' : self.data._id,
			'label' : self.el.getElement('.category_label input').get('value'),
			'required' : self.el.getElement('.category_required input').get('value'),
			'preferred' : self.el.getElement('.category_preferred input').get('value'),
			'ignored' : self.el.getElement('.category_ignored input').get('value'),
			'destination': self.data.destination
		}
	},

	del: function(){
		var self = this;

		if(self.data.label == undefined){
			self.el.destroy();
			return;
		}

		var label = self.el.getElement('.category_label input').get('value');
		var qObj = new Question('Are you sure you want to delete <strong>"'+label+'"</strong>?', '', [{
			'text': 'Delete "'+label+'"',
			'class': 'delete',
			'events': {
				'click': function(e){
					(e).preventDefault();
					Api.request('category.delete', {
						'data': {
							'id': self.data._id
						},
						'useSpinner': true,
						'spinnerOptions': {
							'target': self.el
						},
						'onComplete': function(json){
							if(json.success) {
								qObj.close();
								self.el.destroy();
							} else {
								alert(json.message);
							}
						}
					});
				}
			}
		}, {
			'text': 'Cancel',
			'cancel': true
		}]);

	},

	makeSortable: function(){
		var self = this;

		self.sortable = new Sortables(self.category_container, {
			'revert': true,
			'handle': '.handle',
			'opacity': 0.5,
			'onComplete': self.save.bind(self, 300)
		});
	},

	get: function(attr){
		return this.data[attr]
	},

	toElement: function(){
		return this.el
	}

});
