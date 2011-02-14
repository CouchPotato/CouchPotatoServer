// MooTools: the javascript framework.
// Load this file's selection again by visiting: http://mootools.net/more/82d3c4f6ee721f808321f6bf6818d8fb 
// Or build this file again with packager using: packager build More/Element.Delegation More/Element.Shortcuts
/*
---

script: More.js

name: More

description: MooTools More

license: MIT-style license

authors:
  - Guillermo Rauch
  - Thomas Aylott
  - Scott Kyle
  - Arian Stolwijk
  - Tim Wienk
  - Christoph Pojer
  - Aaron Newton

requires:
  - Core/MooTools

provides: [MooTools.More]

...
*/

MooTools.More = {
	'version': '1.3.0.1',
	'build': '6dce99bed2792dffcbbbb4ddc15a1fb9a41994b5'
};


/*
---

name: Events.Pseudos

description: Adds the functionallity to add pseudo events

license: MIT-style license

authors:
  - Arian Stolwijk

requires: [Core/Class.Extras, Core/Slick.Parser, More/MooTools.More]

provides: [Events.Pseudos]

...
*/

Events.Pseudos = function(pseudos, addEvent, removeEvent){

	var storeKey = 'monitorEvents:';

	var storageOf = function(object){

		return {
			store: object.store ? function(key, value){
				object.store(storeKey + key, value);
			} : function(key, value){
				(object.$monitorEvents || (object.$monitorEvents = {}))[key] = value;
			},
			retrieve: object.retrieve ? function(key, dflt){
				return object.retrieve(storeKey + key, dflt);
			} : function(key, dflt){
				if (!object.$monitorEvents) return dflt;
				return object.$monitorEvents[key] || dflt;
			}
		};
	};


	var splitType = function(type){
		if (type.indexOf(':') == -1) return null;

		var parsed = Slick.parse(type).expressions[0][0],
			parsedPseudos = parsed.pseudos;

		return (pseudos && pseudos[parsedPseudos[0].key]) ? {
			event: parsed.tag,
			value: parsedPseudos[0].value,
			pseudo: parsedPseudos[0].key,
			original: type
		} : null;
	};


	return {

		addEvent: function(type, fn, internal){
			var split = splitType(type);
			if (!split) return addEvent.call(this, type, fn, internal);

			var storage = storageOf(this),
				events = storage.retrieve(type, []),
				pseudoArgs = Array.from(pseudos[split.pseudo]),
				proxy = pseudoArgs[1];

			var self = this;
			var monitor = function(){
				pseudoArgs[0].call(self, split, fn, arguments, proxy);
			};

			events.include({event: fn, monitor: monitor});
			storage.store(type, events);

			var eventType = split.event;
			if (proxy && proxy[eventType]) eventType = proxy[eventType].base;

			addEvent.call(this, type, fn, internal);
			return addEvent.call(this, eventType, monitor, internal);
		},

		removeEvent: function(type, fn){
			var split = splitType(type);
			if (!split) return removeEvent.call(this, type, fn);

			var storage = storageOf(this),
				events = storage.retrieve(type),
				pseudoArgs = Array.from(pseudos[split.pseudo]),
				proxy = pseudoArgs[1];

			if (!events) return this;

			var eventType = split.event;
			if (proxy && proxy[eventType]) eventType = proxy[eventType].base;

			removeEvent.call(this, type, fn);
			events.each(function(monitor, i){
				if (!fn || monitor.event == fn) removeEvent.call(this, eventType, monitor.monitor);
				delete events[i];
			}, this);

			storage.store(type, events);
			return this;
		}

	};

};

(function(){

var pseudos = {

	once: function(split, fn, args){
		fn.apply(this, args);
		this.removeEvent(split.original, fn);
	}

};

Events.definePseudo = function(key, fn){
	pseudos[key] = fn;
};

var proto = Events.prototype;
Events.implement(Events.Pseudos(pseudos, proto.addEvent, proto.removeEvent));

})();


/*
---

name: Element.Event.Pseudos

description: Adds the functionality to add pseudo events for Elements

license: MIT-style license

authors:
  - Arian Stolwijk

requires: [Core/Element.Event, Events.Pseudos]

provides: [Element.Event.Pseudos]

...
*/

(function(){

var pseudos = {

	once: function(split, fn, args){
		fn.apply(this, args);
		this.removeEvent(split.original, fn);
	}

};

Event.definePseudo = function(key, fn, proxy){
	pseudos[key] = [fn, proxy];
};

var proto = Element.prototype;
[Element, Window, Document].invoke('implement', Events.Pseudos(pseudos, proto.addEvent, proto.removeEvent));

})();


/*
---

script: Element.Delegation.js

name: Element.Delegation

description: Extends the Element native object to include the delegate method for more efficient event management.

credits:
  - "Event checking based on the work of Daniel Steigerwald. License: MIT-style license. Copyright: Copyright (c) 2008 Daniel Steigerwald, daniel.steigerwald.cz"

license: MIT-style license

authors:
  - Aaron Newton
  - Daniel Steigerwald

requires: [/MooTools.More, Element.Event.Pseudos]

provides: [Element.Delegation]

...
*/


Event.definePseudo('relay', function(split, fn, args, proxy){
	var event = args[0];
	var check = proxy ? proxy.condition : null;

	for (var target = event.target; target && target != this; target = target.parentNode){
		var finalTarget = document.id(target);
		if (Slick.match(target, split.value) && (!check || check.call(finalTarget, event))){
			if (finalTarget) fn.call(finalTarget, event, finalTarget);
			return;
		}
	}

}, {
	mouseenter: {
		base: 'mouseover',
		condition: Element.Events.mouseenter.condition
	},
	mouseleave: {
		base: 'mouseout',
		condition: Element.Events.mouseleave.condition
	}
});


/*
---

script: Element.Shortcuts.js

name: Element.Shortcuts

description: Extends the Element native object to include some shortcut methods.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Element.Style
  - /MooTools.More

provides: [Element.Shortcuts]

...
*/

Element.implement({

	isDisplayed: function(){
		return this.getStyle('display') != 'none';
	},

	isVisible: function(){
		var w = this.offsetWidth,
			h = this.offsetHeight;
		return (w == 0 && h == 0) ? false : (w > 0 && h > 0) ? true : this.style.display != 'none';
	},

	toggle: function(){
		return this[this.isDisplayed() ? 'hide' : 'show']();
	},

	hide: function(){
		var d;
		try {
			//IE fails here if the element is not in the dom
			d = this.getStyle('display');
		} catch(e){}
		if (d == 'none') return this;
		return this.store('element:_originalDisplay', d || '').setStyle('display', 'none');
	},

	show: function(display){
		if (!display && this.isDisplayed()) return this;
		display = display || this.retrieve('element:_originalDisplay') || 'block';
		return this.setStyle('display', (display == 'none') ? 'block' : display);
	},

	swapClass: function(remove, add){
		return this.removeClass(remove).addClass(add);
	}

});

Document.implement({

	clearSelection: function(){
		if (document.selection && document.selection.empty){
			document.selection.empty();
		} else if (window.getSelection){
			var selection = window.getSelection();
			if (selection && selection.removeAllRanges) selection.removeAllRanges();
		}
	}

});

