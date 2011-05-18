var File = new Class({

	initialize: function(file){
		var self = this;

		self.data = file;
		self.type = File.Type.get(file.type_id);

		self['create'+(self.type.type).capitalize()]()

	},

	createImage: function(){
		var self = this;

		self.el = new Element('div', {
			'class': 'type_image ' + self.type.identifier
		}).adopt(
			new Element('img', {
				'src': Api.createUrl('file.cache') + self.data.path.substring(1) + '/'
			})
		)
	},

	toElement: function(){
		return this.el;
	}

});

var FileSelect = new Class({

	multiple: function(type, files, single){

		var results = files.filter(function(file){
			return file.type_id == File.Type.get(type).id;
		});

		if(single)
			return new File(results.pop());

		return results;

	},

	single: function(type, files){
		return this.multiple(type, files, true);
	}

});
window.File.Select = new FileSelect();

var FileTypeBase = new Class({

	setup: function(types){
		var self = this;

		self.typesById = {};
		self.typesByKey = {};
		Object.each(types, function(type){
			self.typesByKey[type.identifier] = type;
			self.typesById[type.id] = type;
		});

	},

	get: function(identifier){
		if(typeOf(identifier) == 'number')
			return this.typesById[identifier]
		else
			return this.typesByKey[identifier]
	}

});
window.File.Type = new FileTypeBase();
