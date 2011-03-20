/*
---

name: EventStack

description: Helps you Escape.

authors: Christoph Pojer (@cpojer)

license: MIT-style license.

requires: [Core/Class.Extras, Core/Element.Event, Class-Extras/Class.Binds]

provides: EventStack

...
*/

(function(){

this.EventStack = new Class({

	Implements: [Options, Class.Binds],

	options: {
		event: 'keyup',
		condition: function(event){
			return (event.key == 'esc');
		}
	},

	initialize: function(options){
		this.setOptions(options);
		this.stack = [];
		this.data = [];

		document.addEvent(this.options.event, this.bound('condition'));
	},

	condition: function(event){
		if (this.options.condition.call(this, event, this.data.getLast()))
			this.pop(event);
	},

	erase: function(fn){
		this.data.erase(this.data[this.stack.indexOf(fn)]);
		this.stack.erase(fn);

		return this;
	},

	push: function(fn, data){
		this.erase(fn);
		this.data.push(data || null);
		this.stack.push(fn);
		
		return this;
	},

	pop: function(event){
		var fn = this.stack.pop(),
			data = this.data.pop();
		
		if (fn) fn.call(this, event, data);

		return this;
	}

});

}).call(this);
