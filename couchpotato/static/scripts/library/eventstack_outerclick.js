/*
---

name: EventStack.OuterClick

description: Helps you escape from clicks outside of a certain area.

authors: Christoph Pojer (@cpojer)

license: MIT-style license.

requires: [EventStack]

provides: EventStack.OuterClick

...
*/

EventStack.OuterClick = new Class({

	Extends: EventStack,

	options: {
		event: 'click',
		condition: function(event, element){
			return element && !element.contains(event.target);
		}
	}

});
