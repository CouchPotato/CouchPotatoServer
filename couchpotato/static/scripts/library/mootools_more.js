// MooTools: the javascript framework.
// Load this file's selection again by visiting: http://mootools.net/more/1e3edb90c5e02d9b9013b54e6ab001ea 
// Or build this file again with packager using: packager build More/Element.Forms More/Element.Delegation More/Element.Shortcuts More/Fx.Slide More/Sortables More/Request.JSONP More/Request.Periodical More/Spinner
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
	'version': '1.3.1.1',
	'build': '0292a3af1eea242b817fecf9daa127417d10d4ce'
};


/*
---

script: String.Extras.js

name: String.Extras

description: Extends the String native object to include methods useful in managing various kinds of strings (query strings, urls, html, etc).

license: MIT-style license

authors:
  - Aaron Newton
  - Guillermo Rauch
  - Christopher Pitt

requires:
  - Core/String
  - Core/Array
  - MooTools.More

provides: [String.Extras]

...
*/

(function(){

var special = {
	'a': /[àáâãäåăą]/g,
	'A': /[ÀÁÂÃÄÅĂĄ]/g,
	'c': /[ćčç]/g,
	'C': /[ĆČÇ]/g,
	'd': /[ďđ]/g,
	'D': /[ĎÐ]/g,
	'e': /[èéêëěę]/g,
	'E': /[ÈÉÊËĚĘ]/g,
	'g': /[ğ]/g,
	'G': /[Ğ]/g,
	'i': /[ìíîï]/g,
	'I': /[ÌÍÎÏ]/g,
	'l': /[ĺľł]/g,
	'L': /[ĹĽŁ]/g,
	'n': /[ñňń]/g,
	'N': /[ÑŇŃ]/g,
	'o': /[òóôõöøő]/g,
	'O': /[ÒÓÔÕÖØ]/g,
	'r': /[řŕ]/g,
	'R': /[ŘŔ]/g,
	's': /[ššş]/g,
	'S': /[ŠŞŚ]/g,
	't': /[ťţ]/g,
	'T': /[ŤŢ]/g,
	'ue': /[ü]/g,
	'UE': /[Ü]/g,
	'u': /[ùúûůµ]/g,
	'U': /[ÙÚÛŮ]/g,
	'y': /[ÿý]/g,
	'Y': /[ŸÝ]/g,
	'z': /[žźż]/g,
	'Z': /[ŽŹŻ]/g,
	'th': /[þ]/g,
	'TH': /[Þ]/g,
	'dh': /[ð]/g,
	'DH': /[Ð]/g,
	'ss': /[ß]/g,
	'oe': /[œ]/g,
	'OE': /[Œ]/g,
	'ae': /[æ]/g,
	'AE': /[Æ]/g
},

tidy = {
	' ': /[\xa0\u2002\u2003\u2009]/g,
	'*': /[\xb7]/g,
	'\'': /[\u2018\u2019]/g,
	'"': /[\u201c\u201d]/g,
	'...': /[\u2026]/g,
	'-': /[\u2013]/g,
//	'--': /[\u2014]/g,
	'&raquo;': /[\uFFFD]/g
};

var walk = function(string, replacements){
	var result = string, key;
	for (key in replacements) result = result.replace(replacements[key], key);
	return result;
};

var getRegexForTag = function(tag, contents){
	tag = tag || '';
	var regstr = contents ? "<" + tag + "(?!\\w)[^>]*>([\\s\\S]*?)<\/" + tag + "(?!\\w)>" : "<\/?" + tag + "([^>]+)?>",
		reg = new RegExp(regstr, "gi");
	return reg;
};

String.implement({

	standardize: function(){
		return walk(this, special);
	},

	repeat: function(times){
		return new Array(times + 1).join(this);
	},

	pad: function(length, str, direction){
		if (this.length >= length) return this;

		var pad = (str == null ? ' ' : '' + str)
			.repeat(length - this.length)
			.substr(0, length - this.length);

		if (!direction || direction == 'right') return this + pad;
		if (direction == 'left') return pad + this;

		return pad.substr(0, (pad.length / 2).floor()) + this + pad.substr(0, (pad.length / 2).ceil());
	},

	getTags: function(tag, contents){
		return this.match(getRegexForTag(tag, contents)) || [];
	},

	stripTags: function(tag, contents){
		return this.replace(getRegexForTag(tag, contents), '');
	},

	tidy: function(){
		return walk(this, tidy);
	},

	truncate: function(max, trail, atChar){
		var string = this;
		if (trail == null && arguments.length == 1) trail = '…';
		if (string.length > max){
			string = string.substring(0, max);
			if (atChar){
				var index = string.lastIndexOf(atChar);
				if (index != -1) string = string.substr(0, index);
			}
			if (trail) string += trail;
		}
		return string;
	}

});

}).call(this);


/*
---

script: Element.Forms.js

name: Element.Forms

description: Extends the Element native object to include methods useful in managing inputs.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Element
  - /String.Extras
  - /MooTools.More

provides: [Element.Forms]

...
*/

Element.implement({

	tidy: function(){
		this.set('value', this.get('value').tidy());
	},

	getTextInRange: function(start, end){
		return this.get('value').substring(start, end);
	},

	getSelectedText: function(){
		if (this.setSelectionRange) return this.getTextInRange(this.getSelectionStart(), this.getSelectionEnd());
		return document.selection.createRange().text;
	},

	getSelectedRange: function(){
		if (this.selectionStart != null){
			return {
				start: this.selectionStart,
				end: this.selectionEnd
			};
		}

		var pos = {
			start: 0,
			end: 0
		};
		var range = this.getDocument().selection.createRange();
		if (!range || range.parentElement() != this) return pos;
		var duplicate = range.duplicate();

		if (this.type == 'text'){
			pos.start = 0 - duplicate.moveStart('character', -100000);
			pos.end = pos.start + range.text.length;
		} else {
			var value = this.get('value');
			var offset = value.length;
			duplicate.moveToElementText(this);
			duplicate.setEndPoint('StartToEnd', range);
			if (duplicate.text.length) offset -= value.match(/[\n\r]*$/)[0].length;
			pos.end = offset - duplicate.text.length;
			duplicate.setEndPoint('StartToStart', range);
			pos.start = offset - duplicate.text.length;
		}
		return pos;
	},

	getSelectionStart: function(){
		return this.getSelectedRange().start;
	},

	getSelectionEnd: function(){
		return this.getSelectedRange().end;
	},

	setCaretPosition: function(pos){
		if (pos == 'end') pos = this.get('value').length;
		this.selectRange(pos, pos);
		return this;
	},

	getCaretPosition: function(){
		return this.getSelectedRange().start;
	},

	selectRange: function(start, end){
		if (this.setSelectionRange){
			this.focus();
			this.setSelectionRange(start, end);
		} else {
			var value = this.get('value');
			var diff = value.substr(start, end - start).replace(/\r/g, '').length;
			start = value.substr(0, start).replace(/\r/g, '').length;
			var range = this.createTextRange();
			range.collapse(true);
			range.moveEnd('character', start + diff);
			range.moveStart('character', start);
			range.select();
		}
		return this;
	},

	insertAtCursor: function(value, select){
		var pos = this.getSelectedRange();
		var text = this.get('value');
		this.set('value', text.substring(0, pos.start) + value + text.substring(pos.end, text.length));
		if (select !== false) this.selectRange(pos.start, pos.start + value.length);
		else this.setCaretPosition(pos.start + value.length);
		return this;
	},

	insertAroundCursor: function(options, select){
		options = Object.append({
			before: '',
			defaultMiddle: '',
			after: ''
		}, options);

		var value = this.getSelectedText() || options.defaultMiddle;
		var pos = this.getSelectedRange();
		var text = this.get('value');

		if (pos.start == pos.end){
			this.set('value', text.substring(0, pos.start) + options.before + value + options.after + text.substring(pos.end, text.length));
			this.selectRange(pos.start + options.before.length, pos.end + options.before.length + value.length);
		} else {
			var current = text.substring(pos.start, pos.end);
			this.set('value', text.substring(0, pos.start) + options.before + current + options.after + text.substring(pos.end, text.length));
			var selStart = pos.start + options.before.length;
			if (select !== false) this.selectRange(selStart, selStart + current.length);
			else this.setCaretPosition(selStart + text.length);
		}
		return this;
	}

});


/*
---

name: Events.Pseudos

description: Adds the functionality to add pseudo events

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
		if (type.indexOf(':') == -1 || !pseudos) return null;

		var parsed = Slick.parse(type).expressions[0][0],
			parsedPseudos = parsed.pseudos,
			l = parsedPseudos.length,
			splits = [];

		while (l--) if (pseudos[parsedPseudos[l].key]){
			splits.push({
				event: parsed.tag,
				value: parsedPseudos[l].value,
				pseudo: parsedPseudos[l].key,
				original: type
			});
		}

		return splits.length ? splits : null;
	};

	var mergePseudoOptions = function(split){
		return Object.merge.apply(this, split.map(function(item){
			return pseudos[item.pseudo].options || {};
		}));
	};

	return {

		addEvent: function(type, fn, internal){
			var split = splitType(type);
			if (!split) return addEvent.call(this, type, fn, internal);

			var storage = storageOf(this),
				events = storage.retrieve(type, []),
				eventType = split[0].event,
				options = mergePseudoOptions(split),
				stack = fn,
				eventOptions = options[eventType] || {},
				args = Array.slice(arguments, 2),
				self = this,
				monitor;

			if (eventOptions.args) args.append(Array.from(eventOptions.args));
			if (eventOptions.base) eventType = eventOptions.base;
			if (eventOptions.onAdd) eventOptions.onAdd(this);

			split.each(function(item){
				var stackFn = stack;
				stack = function(){
					(eventOptions.listener || pseudos[item.pseudo].listener).call(self, item, stackFn, arguments, monitor, options);
				};
			});
			monitor = stack.bind(this);

			events.include({event: fn, monitor: monitor});
			storage.store(type, events);

			addEvent.apply(this, [type, fn].concat(args));
			return addEvent.apply(this, [eventType, monitor].concat(args));
		},

		removeEvent: function(type, fn){
			var split = splitType(type);
			if (!split) return removeEvent.call(this, type, fn);

			var storage = storageOf(this),
				events = storage.retrieve(type);
			if (!events) return this;

			var eventType = split[0].event,
				options = mergePseudoOptions(split),
				eventOptions = options[eventType] || {},
				args = Array.slice(arguments, 2);

			if (eventOptions.args) args.append(Array.from(eventOptions.args));
			if (eventOptions.base) eventType = eventOptions.base;
			if (eventOptions.onRemove) eventOptions.onRemove(this);

			removeEvent.apply(this, [type, fn].concat(args));
			events.each(function(monitor, i){
				if (!fn || monitor.event == fn) removeEvent.apply(this, [eventType, monitor.monitor].concat(args));
				delete events[i];
			}, this);

			storage.store(type, events);
			return this;
		}

	};

};

(function(){

var pseudos = {

	once: {
		listener: function(split, fn, args, monitor){
			fn.apply(this, args);
			this.removeEvent(split.event, monitor)
				.removeEvent(split.original, fn);
		}
	},

	throttle: {
		listener: function(split, fn, args){
			if (!fn._throttled){
				fn.apply(this, args);
				fn._throttled = setTimeout(function(){
					fn._throttled = false;
				}, split.value || 250);
			}
		}
	},

	pause: {
		listener: function(split, fn, args){
			clearTimeout(fn._pause);
			fn._pause = fn.delay(split.value || 250, this, args);
		}
	}

};

Events.definePseudo = function(key, listener){
	pseudos[key] = Type.isFunction(listener) ? {listener: listener} : listener;
	return this;
};

Events.lookupPseudo = function(key){
	return pseudos[key];
};

var proto = Events.prototype;
Events.implement(Events.Pseudos(pseudos, proto.addEvent, proto.removeEvent));

['Request', 'Fx'].each(function(klass){
	if (this[klass]) this[klass].implement(Events.prototype);
});

}).call(this);


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

var pseudos = {},
	copyFromEvents = ['once', 'throttle', 'pause'],
	count = copyFromEvents.length;

while (count--) pseudos[copyFromEvents[count]] = Events.lookupPseudo(copyFromEvents[count]);

Event.definePseudo = function(key, listener){
	pseudos[key] = Type.isFunction(listener) ? {listener: listener} : listener;
	return this;
};

var proto = Element.prototype;
[Element, Window, Document].invoke('implement', Events.Pseudos(pseudos, proto.addEvent, proto.removeEvent));

}).call(this);


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

(function(){

var eventListenerSupport = !(window.attachEvent && !window.addEventListener),
	nativeEvents = Element.NativeEvents;

nativeEvents.focusin = 2;
nativeEvents.focusout = 2;

var check = function(split, target, event){
	var elementEvent = Element.Events[split.event], condition;
	if (elementEvent) condition = elementEvent.condition;
	return Slick.match(target, split.value) && (!condition || condition.call(target, event));
};

var formObserver = function(eventName){

	var $delegationKey = '$delegation:';

	return {
		base: 'focusin',

		onRemove: function(element){
			element.retrieve($delegationKey + 'forms', []).each(function(el){
				el.retrieve($delegationKey + 'listeners', []).each(function(listener){
					el.removeEvent(eventName, listener);
				});
				el.eliminate($delegationKey + eventName + 'listeners')
					.eliminate($delegationKey + eventName + 'originalFn');
			});
		},

		listener: function(split, fn, args, monitor, options){
			var event = args[0],
				forms = this.retrieve($delegationKey + 'forms', []),
				target = event.target,
				form = (target.get('tag') == 'form') ? target : event.target.getParent('form'),
				formEvents = form.retrieve($delegationKey + 'originalFn', []),
				formListeners = form.retrieve($delegationKey + 'listeners', []);

			forms.include(form);
			this.store($delegationKey + 'forms', forms);

			if (!formEvents.contains(fn)){
				var formListener = function(event){
					if (check(split, this, event)) fn.call(this, event);
				};
				form.addEvent(eventName, formListener);

				formEvents.push(fn);
				formListeners.push(formListener);

				form.store($delegationKey + eventName + 'originalFn', formEvents)
					.store($delegationKey + eventName + 'listeners', formListeners);
			}
		}
	};
};

var inputObserver = function(eventName){
	return {
		base: 'focusin',
		listener: function(split, fn, args){
			var events = {blur: function(){
				this.removeEvents(events);
			}};
			events[eventName] = function(event){
				if (check(split, this, event)) fn.call(this, event);
			};
			args[0].target.addEvents(events);
		}
	};
};

var eventOptions = {
	mouseenter: {
		base: 'mouseover'
	},
	mouseleave: {
		base: 'mouseout'
	},
	focus: {
		base: 'focus' + (eventListenerSupport ? '' : 'in'),
		args: [true]
	},
	blur: {
		base: eventListenerSupport ? 'blur' : 'focusout',
		args: [true]
	}
};

if (!eventListenerSupport) Object.append(eventOptions, {
	submit: formObserver('submit'),
	reset: formObserver('reset'),
	change: inputObserver('change'),
	select: inputObserver('select')
});


Event.definePseudo('relay', {
	listener: function(split, fn, args, monitor, options){
		var event = args[0];

		for (var target = event.target; target && target != this; target = target.parentNode){
			var finalTarget = document.id(target);
			if (check(split, finalTarget, event)){
				if (finalTarget) fn.call(finalTarget, event, finalTarget);
				return;
			}
		}
	},
	options: eventOptions
});

}).call(this);



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
		if (window.getSelection){
			var selection = window.getSelection();
			if (selection && selection.removeAllRanges) selection.removeAllRanges();
		} else if (document.selection && document.selection.empty){
			try {
				//IE fails here if selected element is not in dom
				document.selection.empty();
			} catch(e){}
		}
	}

});


/*
---

script: Fx.Slide.js

name: Fx.Slide

description: Effect to slide an element in and out of view.

license: MIT-style license

authors:
  - Valerio Proietti

requires:
  - Core/Fx
  - Core/Element.Style
  - /MooTools.More

provides: [Fx.Slide]

...
*/

Fx.Slide = new Class({

	Extends: Fx,

	options: {
		mode: 'vertical',
		wrapper: false,
		hideOverflow: true,
		resetHeight: false
	},

	initialize: function(element, options){
		element = this.element = this.subject = document.id(element);
		this.parent(options);
		options = this.options;

		var wrapper = element.retrieve('wrapper'),
			styles = element.getStyles('margin', 'position', 'overflow');

		if (options.hideOverflow) styles = Object.append(styles, {overflow: 'hidden'});
		if (options.wrapper) wrapper = document.id(options.wrapper).setStyles(styles);

		if (!wrapper) wrapper = new Element('div', {
			styles: styles
		}).wraps(element);

		element.store('wrapper', wrapper).setStyle('margin', 0);
		if (element.getStyle('overflow') == 'visible') element.setStyle('overflow', 'hidden');

		this.now = [];
		this.open = true;
		this.wrapper = wrapper;

		this.addEvent('complete', function(){
			this.open = (wrapper['offset' + this.layout.capitalize()] != 0);
			if (this.open && options.resetHeight) wrapper.setStyle('height', '');
		}, true);
	},

	vertical: function(){
		this.margin = 'margin-top';
		this.layout = 'height';
		this.offset = this.element.offsetHeight;
	},

	horizontal: function(){
		this.margin = 'margin-left';
		this.layout = 'width';
		this.offset = this.element.offsetWidth;
	},

	set: function(now){
		this.element.setStyle(this.margin, now[0]);
		this.wrapper.setStyle(this.layout, now[1]);
		return this;
	},

	compute: function(from, to, delta){
		return [0, 1].map(function(i){
			return Fx.compute(from[i], to[i], delta);
		});
	},

	start: function(how, mode){
		if (!this.check(how, mode)) return this;
		this[mode || this.options.mode]();

		var margin = this.element.getStyle(this.margin).toInt(),
			layout = this.wrapper.getStyle(this.layout).toInt(),
			caseIn = [[margin, layout], [0, this.offset]],
			caseOut = [[margin, layout], [-this.offset, 0]],
			start;

		switch (how){
			case 'in': start = caseIn; break;
			case 'out': start = caseOut; break;
			case 'toggle': start = (layout == 0) ? caseIn : caseOut;
		}
		return this.parent(start[0], start[1]);
	},

	slideIn: function(mode){
		return this.start('in', mode);
	},

	slideOut: function(mode){
		return this.start('out', mode);
	},

	hide: function(mode){
		this[mode || this.options.mode]();
		this.open = false;
		return this.set([-this.offset, 0]);
	},

	show: function(mode){
		this[mode || this.options.mode]();
		this.open = true;
		return this.set([0, this.offset]);
	},

	toggle: function(mode){
		return this.start('toggle', mode);
	}

});

Element.Properties.slide = {

	set: function(options){
		this.get('slide').cancel().setOptions(options);
		return this;
	},

	get: function(){
		var slide = this.retrieve('slide');
		if (!slide){
			slide = new Fx.Slide(this, {link: 'cancel'});
			this.store('slide', slide);
		}
		return slide;
	}

};

Element.implement({

	slide: function(how, mode){
		how = how || 'toggle';
		var slide = this.get('slide'), toggle;
		switch (how){
			case 'hide': slide.hide(mode); break;
			case 'show': slide.show(mode); break;
			case 'toggle':
				var flag = this.retrieve('slide:flag', slide.open);
				slide[flag ? 'slideOut' : 'slideIn'](mode);
				this.store('slide:flag', !flag);
				toggle = true;
			break;
			default: slide.start(how, mode);
		}
		if (!toggle) this.eliminate('slide:flag');
		return this;
	}

});


/*
---

script: Drag.js

name: Drag

description: The base Drag Class. Can be used to drag and resize Elements using mouse events.

license: MIT-style license

authors:
  - Valerio Proietti
  - Tom Occhinno
  - Jan Kassens

requires:
  - Core/Events
  - Core/Options
  - Core/Element.Event
  - Core/Element.Style
  - Core/Element.Dimensions
  - /MooTools.More

provides: [Drag]
...

*/

var Drag = new Class({

	Implements: [Events, Options],

	options: {/*
		onBeforeStart: function(thisElement){},
		onStart: function(thisElement, event){},
		onSnap: function(thisElement){},
		onDrag: function(thisElement, event){},
		onCancel: function(thisElement){},
		onComplete: function(thisElement, event){},*/
		snap: 6,
		unit: 'px',
		grid: false,
		style: true,
		limit: false,
		handle: false,
		invert: false,
		preventDefault: false,
		stopPropagation: false,
		modifiers: {x: 'left', y: 'top'}
	},

	initialize: function(){
		var params = Array.link(arguments, {
			'options': Type.isObject,
			'element': function(obj){
				return obj != null;
			}
		});

		this.element = document.id(params.element);
		this.document = this.element.getDocument();
		this.setOptions(params.options || {});
		var htype = typeOf(this.options.handle);
		this.handles = ((htype == 'array' || htype == 'collection') ? $$(this.options.handle) : document.id(this.options.handle)) || this.element;
		this.mouse = {'now': {}, 'pos': {}};
		this.value = {'start': {}, 'now': {}};

		this.selection = (Browser.ie) ? 'selectstart' : 'mousedown';


		if (Browser.ie && !Drag.ondragstartFixed){
			document.ondragstart = Function.from(false);
			Drag.ondragstartFixed = true;
		}

		this.bound = {
			start: this.start.bind(this),
			check: this.check.bind(this),
			drag: this.drag.bind(this),
			stop: this.stop.bind(this),
			cancel: this.cancel.bind(this),
			eventStop: Function.from(false)
		};
		this.attach();
	},

	attach: function(){
		this.handles.addEvent('mousedown', this.bound.start);
		return this;
	},

	detach: function(){
		this.handles.removeEvent('mousedown', this.bound.start);
		return this;
	},

	start: function(event){
		var options = this.options;

		if (event.rightClick) return;

		if (options.preventDefault) event.preventDefault();
		if (options.stopPropagation) event.stopPropagation();
		this.mouse.start = event.page;

		this.fireEvent('beforeStart', this.element);

		var limit = options.limit;
		this.limit = {x: [], y: []};

		var styles = this.element.getStyles('left', 'right', 'top', 'bottom');
		this._invert = {
			x: options.modifiers.x == 'left' && styles.left == 'auto' && !isNaN(styles.right.toInt()) && (options.modifiers.x = 'right'),
			y: options.modifiers.y == 'top' && styles.top == 'auto' && !isNaN(styles.bottom.toInt()) && (options.modifiers.y = 'bottom')
		};

		var z, coordinates;
		for (z in options.modifiers){
			if (!options.modifiers[z]) continue;

			var style = this.element.getStyle(options.modifiers[z]);

			// Some browsers (IE and Opera) don't always return pixels.
			if (style && !style.match(/px$/)){
				if (!coordinates) coordinates = this.element.getCoordinates(this.element.getOffsetParent());
				style = coordinates[options.modifiers[z]];
			}

			if (options.style) this.value.now[z] = (style || 0).toInt();
			else this.value.now[z] = this.element[options.modifiers[z]];

			if (options.invert) this.value.now[z] *= -1;
			if (this._invert[z]) this.value.now[z] *= -1;

			this.mouse.pos[z] = event.page[z] - this.value.now[z];

			if (limit && limit[z]){
				var i = 2;
				while (i--){
					var limitZI = limit[z][i];
					if (limitZI || limitZI === 0) this.limit[z][i] = (typeof limitZI == 'function') ? limitZI() : limitZI;
				}
			}
		}

		if (typeOf(this.options.grid) == 'number') this.options.grid = {
			x: this.options.grid,
			y: this.options.grid
		};

		var events = {
			mousemove: this.bound.check,
			mouseup: this.bound.cancel
		};
		events[this.selection] = this.bound.eventStop;
		this.document.addEvents(events);
	},

	check: function(event){
		if (this.options.preventDefault) event.preventDefault();
		var distance = Math.round(Math.sqrt(Math.pow(event.page.x - this.mouse.start.x, 2) + Math.pow(event.page.y - this.mouse.start.y, 2)));
		if (distance > this.options.snap){
			this.cancel();
			this.document.addEvents({
				mousemove: this.bound.drag,
				mouseup: this.bound.stop
			});
			this.fireEvent('start', [this.element, event]).fireEvent('snap', this.element);
		}
	},

	drag: function(event){
		var options = this.options;

		if (options.preventDefault) event.preventDefault();
		this.mouse.now = event.page;

		for (var z in options.modifiers){
			if (!options.modifiers[z]) continue;
			this.value.now[z] = this.mouse.now[z] - this.mouse.pos[z];

			if (options.invert) this.value.now[z] *= -1;
			if (this._invert[z]) this.value.now[z] *= -1;

			if (options.limit && this.limit[z]){
				if ((this.limit[z][1] || this.limit[z][1] === 0) && (this.value.now[z] > this.limit[z][1])){
					this.value.now[z] = this.limit[z][1];
				} else if ((this.limit[z][0] || this.limit[z][0] === 0) && (this.value.now[z] < this.limit[z][0])){
					this.value.now[z] = this.limit[z][0];
				}
			}

			if (options.grid[z]) this.value.now[z] -= ((this.value.now[z] - (this.limit[z][0]||0)) % options.grid[z]);

			if (options.style) this.element.setStyle(options.modifiers[z], this.value.now[z] + options.unit);
			else this.element[options.modifiers[z]] = this.value.now[z];
		}

		this.fireEvent('drag', [this.element, event]);
	},

	cancel: function(event){
		this.document.removeEvents({
			mousemove: this.bound.check,
			mouseup: this.bound.cancel
		});
		if (event){
			this.document.removeEvent(this.selection, this.bound.eventStop);
			this.fireEvent('cancel', this.element);
		}
	},

	stop: function(event){
		var events = {
			mousemove: this.bound.drag,
			mouseup: this.bound.stop
		};
		events[this.selection] = this.bound.eventStop;
		this.document.removeEvents(events);
		if (event) this.fireEvent('complete', [this.element, event]);
	}

});

Element.implement({

	makeResizable: function(options){
		var drag = new Drag(this, Object.merge({
			modifiers: {
				x: 'width',
				y: 'height'
			}
		}, options));

		this.store('resizer', drag);
		return drag.addEvent('drag', function(){
			this.fireEvent('resize', drag);
		}.bind(this));
	}

});


/*
---

script: Drag.Move.js

name: Drag.Move

description: A Drag extension that provides support for the constraining of draggables to containers and droppables.

license: MIT-style license

authors:
  - Valerio Proietti
  - Tom Occhinno
  - Jan Kassens
  - Aaron Newton
  - Scott Kyle

requires:
  - Core/Element.Dimensions
  - /Drag

provides: [Drag.Move]

...
*/

Drag.Move = new Class({

	Extends: Drag,

	options: {/*
		onEnter: function(thisElement, overed){},
		onLeave: function(thisElement, overed){},
		onDrop: function(thisElement, overed, event){},*/
		droppables: [],
		container: false,
		precalculate: false,
		includeMargins: true,
		checkDroppables: true
	},

	initialize: function(element, options){
		this.parent(element, options);
		element = this.element;

		this.droppables = $$(this.options.droppables);
		this.container = document.id(this.options.container);

		if (this.container && typeOf(this.container) != 'element')
			this.container = document.id(this.container.getDocument().body);

		if (this.options.style){
			if (this.options.modifiers.x == "left" && this.options.modifiers.y == "top"){
				var parentStyles,
					parent = element.getOffsetParent();
				var styles = element.getStyles('left', 'top');
				if (parent && (styles.left == 'auto' || styles.top == 'auto')){
					element.setPosition(element.getPosition(parent));
				}
			}

			if (element.getStyle('position') == 'static') element.setStyle('position', 'absolute');
		}

		this.addEvent('start', this.checkDroppables, true);
		this.overed = null;
	},

	start: function(event){
		if (this.container) this.options.limit = this.calculateLimit();

		if (this.options.precalculate){
			this.positions = this.droppables.map(function(el){
				return el.getCoordinates();
			});
		}

		this.parent(event);
	},

	calculateLimit: function(){
		var element = this.element,
			container = this.container,

			offsetParent = document.id(element.getOffsetParent()) || document.body,
			containerCoordinates = container.getCoordinates(offsetParent),
			elementMargin = {},
			elementBorder = {},
			containerMargin = {},
			containerBorder = {},
			offsetParentPadding = {};

		['top', 'right', 'bottom', 'left'].each(function(pad){
			elementMargin[pad] = element.getStyle('margin-' + pad).toInt();
			elementBorder[pad] = element.getStyle('border-' + pad).toInt();
			containerMargin[pad] = container.getStyle('margin-' + pad).toInt();
			containerBorder[pad] = container.getStyle('border-' + pad).toInt();
			offsetParentPadding[pad] = offsetParent.getStyle('padding-' + pad).toInt();
		}, this);

		var width = element.offsetWidth + elementMargin.left + elementMargin.right,
			height = element.offsetHeight + elementMargin.top + elementMargin.bottom,
			left = 0,
			top = 0,
			right = containerCoordinates.right - containerBorder.right - width,
			bottom = containerCoordinates.bottom - containerBorder.bottom - height;

		if (this.options.includeMargins){
			left += elementMargin.left;
			top += elementMargin.top;
		} else {
			right += elementMargin.right;
			bottom += elementMargin.bottom;
		}

		if (element.getStyle('position') == 'relative'){
			var coords = element.getCoordinates(offsetParent);
			coords.left -= element.getStyle('left').toInt();
			coords.top -= element.getStyle('top').toInt();

			left -= coords.left;
			top -= coords.top;
			if (container.getStyle('position') != 'relative'){
				left += containerBorder.left;
				top += containerBorder.top;
			}
			right += elementMargin.left - coords.left;
			bottom += elementMargin.top - coords.top;

			if (container != offsetParent){
				left += containerMargin.left + offsetParentPadding.left;
				top += ((Browser.ie6 || Browser.ie7) ? 0 : containerMargin.top) + offsetParentPadding.top;
			}
		} else {
			left -= elementMargin.left;
			top -= elementMargin.top;
			if (container != offsetParent){
				left += containerCoordinates.left + containerBorder.left;
				top += containerCoordinates.top + containerBorder.top;
			}
		}

		return {
			x: [left, right],
			y: [top, bottom]
		};
	},

	getDroppableCoordinates: function(element){
		var position = element.getCoordinates();
		if (element.getStyle('position') == 'fixed'){
			var scroll = window.getScroll();
			position.left += scroll.x;
			position.right += scroll.x;
			position.top += scroll.y;
			position.bottom += scroll.y;
		}
		return position;
	},

	checkDroppables: function(){
		var overed = this.droppables.filter(function(el, i){
			el = this.positions ? this.positions[i] : this.getDroppableCoordinates(el);
			var now = this.mouse.now;
			return (now.x > el.left && now.x < el.right && now.y < el.bottom && now.y > el.top);
		}, this).getLast();

		if (this.overed != overed){
			if (this.overed) this.fireEvent('leave', [this.element, this.overed]);
			if (overed) this.fireEvent('enter', [this.element, overed]);
			this.overed = overed;
		}
	},

	drag: function(event){
		this.parent(event);
		if (this.options.checkDroppables && this.droppables.length) this.checkDroppables();
	},

	stop: function(event){
		this.checkDroppables();
		this.fireEvent('drop', [this.element, this.overed, event]);
		this.overed = null;
		return this.parent(event);
	}

});

Element.implement({

	makeDraggable: function(options){
		var drag = new Drag.Move(this, options);
		this.store('dragger', drag);
		return drag;
	}

});


/*
---

script: Sortables.js

name: Sortables

description: Class for creating a drag and drop sorting interface for lists of items.

license: MIT-style license

authors:
  - Tom Occhino

requires:
  - Core/Fx.Morph
  - /Drag.Move

provides: [Sortables]

...
*/

var Sortables = new Class({

	Implements: [Events, Options],

	options: {/*
		onSort: function(element, clone){},
		onStart: function(element, clone){},
		onComplete: function(element){},*/
		opacity: 1,
		clone: false,
		revert: false,
		handle: false,
		dragOptions: {}
	},

	initialize: function(lists, options){
		this.setOptions(options);

		this.elements = [];
		this.lists = [];
		this.idle = true;

		this.addLists($$(document.id(lists) || lists));

		if (!this.options.clone) this.options.revert = false;
		if (this.options.revert) this.effect = new Fx.Morph(null, Object.merge({
			duration: 250,
			link: 'cancel'
		}, this.options.revert));
	},

	attach: function(){
		this.addLists(this.lists);
		return this;
	},

	detach: function(){
		this.lists = this.removeLists(this.lists);
		return this;
	},

	addItems: function(){
		Array.flatten(arguments).each(function(element){
			this.elements.push(element);
			var start = element.retrieve('sortables:start', function(event){
				this.start.call(this, event, element);
			}.bind(this));
			(this.options.handle ? element.getElement(this.options.handle) || element : element).addEvent('mousedown', start);
		}, this);
		return this;
	},

	addLists: function(){
		Array.flatten(arguments).each(function(list){
			this.lists.include(list);
			this.addItems(list.getChildren());
		}, this);
		return this;
	},

	removeItems: function(){
		return $$(Array.flatten(arguments).map(function(element){
			this.elements.erase(element);
			var start = element.retrieve('sortables:start');
			(this.options.handle ? element.getElement(this.options.handle) || element : element).removeEvent('mousedown', start);

			return element;
		}, this));
	},

	removeLists: function(){
		return $$(Array.flatten(arguments).map(function(list){
			this.lists.erase(list);
			this.removeItems(list.getChildren());

			return list;
		}, this));
	},

	getClone: function(event, element){
		if (!this.options.clone) return new Element(element.tagName).inject(document.body);
		if (typeOf(this.options.clone) == 'function') return this.options.clone.call(this, event, element, this.list);
		var clone = element.clone(true).setStyles({
			margin: 0,
			position: 'absolute',
			visibility: 'hidden',
			width: element.getStyle('width')
		}).addEvent('mousedown', function(event){
			element.fireEvent('mousedown', event);
		});
		//prevent the duplicated radio inputs from unchecking the real one
		if (clone.get('html').test('radio')){
			clone.getElements('input[type=radio]').each(function(input, i){
				input.set('name', 'clone_' + i);
				if (input.get('checked')) element.getElements('input[type=radio]')[i].set('checked', true);
			});
		}

		return clone.inject(this.list).setPosition(element.getPosition(element.getOffsetParent()));
	},

	getDroppables: function(){
		var droppables = this.list.getChildren().erase(this.clone).erase(this.element);
		if (!this.options.constrain) droppables.append(this.lists).erase(this.list);
		return droppables;
	},

	insert: function(dragging, element){
		var where = 'inside';
		if (this.lists.contains(element)){
			this.list = element;
			this.drag.droppables = this.getDroppables();
		} else {
			where = this.element.getAllPrevious().contains(element) ? 'before' : 'after';
		}
		this.element.inject(element, where);
		this.fireEvent('sort', [this.element, this.clone]);
	},

	start: function(event, element){
		if (
			!this.idle ||
			event.rightClick ||
			['button', 'input', 'a'].contains(event.target.get('tag'))
		) return;

		this.idle = false;
		this.element = element;
		this.opacity = element.get('opacity');
		this.list = element.getParent();
		this.clone = this.getClone(event, element);

		this.drag = new Drag.Move(this.clone, Object.merge({
			
			droppables: this.getDroppables()
		}, this.options.dragOptions)).addEvents({
			onSnap: function(){
				event.stop();
				this.clone.setStyle('visibility', 'visible');
				this.element.set('opacity', this.options.opacity || 0);
				this.fireEvent('start', [this.element, this.clone]);
			}.bind(this),
			onEnter: this.insert.bind(this),
			onCancel: this.end.bind(this),
			onComplete: this.end.bind(this)
		});

		this.clone.inject(this.element, 'before');
		this.drag.start(event);
	},

	end: function(){
		this.drag.detach();
		this.element.set('opacity', this.opacity);
		if (this.effect){
			var dim = this.element.getStyles('width', 'height'),
				clone = this.clone,
				pos = clone.computePosition(this.element.getPosition(this.clone.getOffsetParent()));

			var destroy = function(){
				this.removeEvent('cancel', destroy);
				clone.destroy();
			};

			this.effect.element = clone;
			this.effect.start({
				top: pos.top,
				left: pos.left,
				width: dim.width,
				height: dim.height,
				opacity: 0.25
			}).addEvent('cancel', destroy).chain(destroy);
		} else {
			this.clone.destroy();
		}
		this.reset();
	},

	reset: function(){
		this.idle = true;
		this.fireEvent('complete', this.element);
	},

	serialize: function(){
		var params = Array.link(arguments, {
			modifier: Type.isFunction,
			index: function(obj){
				return obj != null;
			}
		});
		var serial = this.lists.map(function(list){
			return list.getChildren().map(params.modifier || function(element){
				return element.get('id');
			}, this);
		}, this);

		var index = params.index;
		if (this.lists.length == 1) index = 0;
		return (index || index === 0) && index >= 0 && index < this.lists.length ? serial[index] : serial;
	}

});


/*
---

script: Request.JSONP.js

name: Request.JSONP

description: Defines Request.JSONP, a class for cross domain javascript via script injection.

license: MIT-style license

authors:
  - Aaron Newton
  - Guillermo Rauch
  - Arian Stolwijk

requires:
  - Core/Element
  - Core/Request
  - MooTools.More

provides: [Request.JSONP]

...
*/

Request.JSONP = new Class({

	Implements: [Chain, Events, Options],

	options: {
	/*
		onRequest: function(src, scriptElement){},
		onComplete: function(data){},
		onSuccess: function(data){},
		onCancel: function(){},
		onTimeout: function(){},
		onError: function(){}, */
		onRequest: function(src){
			if (this.options.log && window.console && console.log){
				console.log('JSONP retrieving script with url:' + src);
			}
		},
		onError: function(src){
			if (this.options.log && window.console && console.warn){
				console.warn('JSONP '+ src +' will fail in Internet Explorer, which enforces a 2083 bytes length limit on URIs');
			}
		},
		url: '',
		callbackKey: 'callback',
		injectScript: document.head,
		data: '',
		link: 'ignore',
		timeout: 0,
		log: false
	},

	initialize: function(options){
		this.setOptions(options);
	},

	send: function(options){
		if (!Request.prototype.check.call(this, options)) return this;
		this.running = true;

		var type = typeOf(options);
		if (type == 'string' || type == 'element') options = {data: options};
		options = Object.merge(this.options, options || {});

		var data = options.data;
		switch (typeOf(data)){
			case 'element': data = document.id(data).toQueryString(); break;
			case 'object': case 'hash': data = Object.toQueryString(data);
		}

		var index = this.index = Request.JSONP.counter++;

		var src = options.url +
			(options.url.test('\\?') ? '&' :'?') +
			(options.callbackKey) +
			'=Request.JSONP.request_map.request_'+ index +
			(data ? '&' + data : '');

		if (src.length > 2083) this.fireEvent('error', src);

		Request.JSONP.request_map['request_' + index] = function(){
			this.success(arguments, index);
		}.bind(this);

		var script = this.getScript(src).inject(options.injectScript);
		this.fireEvent('request', [src, script]);

		if (options.timeout) this.timeout.delay(options.timeout, this);

		return this;
	},

	getScript: function(src){
		if (!this.script) this.script = new Element('script[type=text/javascript]', {
			async: true,
			src: src
		});
		return this.script;
	},

	success: function(args, index){
		if (!this.running) return false;
		this.clear()
			.fireEvent('complete', args).fireEvent('success', args)
			.callChain();
	},

	cancel: function(){
		if (this.running) this.clear().fireEvent('cancel');
		return this;
	},

	isRunning: function(){
		return !!this.running;
	},

	clear: function(){
		this.running = false;
		if (this.script){
			this.script.destroy();
			this.script = null;
		}
		return this;
	},

	timeout: function(){
		if (this.running){
			this.running = false;
			this.fireEvent('timeout', [this.script.get('src'), this.script]).fireEvent('failure').cancel();
		}
		return this;
	}

});

Request.JSONP.counter = 0;
Request.JSONP.request_map = {};


/*
---

script: Request.Periodical.js

name: Request.Periodical

description: Requests the same URL to pull data from a server but increases the intervals if no data is returned to reduce the load

license: MIT-style license

authors:
  - Christoph Pojer

requires:
  - Core/Request
  - /MooTools.More

provides: [Request.Periodical]

...
*/

Request.implement({

	options: {
		initialDelay: 5000,
		delay: 5000,
		limit: 60000
	},

	startTimer: function(data){
		var fn = function(){
			if (!this.running) this.send({data: data});
		};
		this.lastDelay = this.options.initialDelay;
		this.timer = fn.delay(this.lastDelay, this);
		this.completeCheck = function(response){
			clearTimeout(this.timer);
			this.lastDelay = (response) ? this.options.delay : (this.lastDelay + this.options.delay).min(this.options.limit);
			this.timer = fn.delay(this.lastDelay, this);
		};
		return this.addEvent('complete', this.completeCheck);
	},

	stopTimer: function(){
		clearTimeout(this.timer);
		return this.removeEvent('complete', this.completeCheck);
	}

});


/*
---

script: Class.Refactor.js

name: Class.Refactor

description: Extends a class onto itself with new property, preserving any items attached to the class's namespace.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Class
  - /MooTools.More

# Some modules declare themselves dependent on Class.Refactor
provides: [Class.refactor, Class.Refactor]

...
*/

Class.refactor = function(original, refactors){

	Object.each(refactors, function(item, name){
		var origin = original.prototype[name];
		if (origin && origin.$origin) origin = origin.$origin;
		original.implement(name, (typeof item == 'function') ? function(){
			var old = this.previous;
			this.previous = origin || function(){};
			var value = item.apply(this, arguments);
			this.previous = old;
			return value;
		} : item);
	});

	return original;

};


/*
---

script: Class.Binds.js

name: Class.Binds

description: Automagically binds specified methods in a class to the instance of the class.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Class
  - /MooTools.More

provides: [Class.Binds]

...
*/

Class.Mutators.Binds = function(binds){
	if (!this.prototype.initialize) this.implement('initialize', function(){});
	return binds;
};

Class.Mutators.initialize = function(initialize){
	return function(){
		Array.from(this.Binds).each(function(name){
			var original = this[name];
			if (original) this[name] = original.bind(this);
		}, this);
		return initialize.apply(this, arguments);
	};
};


/*
---

script: Element.Measure.js

name: Element.Measure

description: Extends the Element native object to include methods useful in measuring dimensions.

credits: "Element.measure / .expose methods by Daniel Steigerwald License: MIT-style license. Copyright: Copyright (c) 2008 Daniel Steigerwald, daniel.steigerwald.cz"

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Element.Style
  - Core/Element.Dimensions
  - /MooTools.More

provides: [Element.Measure]

...
*/

(function(){

var getStylesList = function(styles, planes){
	var list = [];
	Object.each(planes, function(directions){
		Object.each(directions, function(edge){
			styles.each(function(style){
				list.push(style + '-' + edge + (style == 'border' ? '-width' : ''));
			});
		});
	});
	return list;
};

var calculateEdgeSize = function(edge, styles){
	var total = 0;
	Object.each(styles, function(value, style){
		if (style.test(edge)) total = total + value.toInt();
	});
	return total;
};

var isVisible = function(el){
	return !!(!el || el.offsetHeight || el.offsetWidth);
};


Element.implement({

	measure: function(fn){
		if (isVisible(this)) return fn.call(this);
		var parent = this.getParent(),
			toMeasure = [];
		while (!isVisible(parent) && parent != document.body){
			toMeasure.push(parent.expose());
			parent = parent.getParent();
		}
		var restore = this.expose(),
			result = fn.call(this);
		restore();
		toMeasure.each(function(restore){
			restore();
		});
		return result;
	},

	expose: function(){
		if (this.getStyle('display') != 'none') return function(){};
		var before = this.style.cssText;
		this.setStyles({
			display: 'block',
			position: 'absolute',
			visibility: 'hidden'
		});
		return function(){
			this.style.cssText = before;
		}.bind(this);
	},

	getDimensions: function(options){
		options = Object.merge({computeSize: false}, options);
		var dim = {x: 0, y: 0};

		var getSize = function(el, options){
			return (options.computeSize) ? el.getComputedSize(options) : el.getSize();
		};

		var parent = this.getParent('body');

		if (parent && this.getStyle('display') == 'none'){
			dim = this.measure(function(){
				return getSize(this, options);
			});
		} else if (parent){
			try { //safari sometimes crashes here, so catch it
				dim = getSize(this, options);
			}catch(e){}
		}

		return Object.append(dim, (dim.x || dim.x === 0) ? {
				width: dim.x,
				height: dim.y
			} : {
				x: dim.width,
				y: dim.height
			}
		);
	},

	getComputedSize: function(options){
		

		options = Object.merge({
			styles: ['padding','border'],
			planes: {
				height: ['top','bottom'],
				width: ['left','right']
			},
			mode: 'both'
		}, options);

		var styles = {},
			size = {width: 0, height: 0},
			dimensions;

		if (options.mode == 'vertical'){
			delete size.width;
			delete options.planes.width;
		} else if (options.mode == 'horizontal'){
			delete size.height;
			delete options.planes.height;
		}

		getStylesList(options.styles, options.planes).each(function(style){
			styles[style] = this.getStyle(style).toInt();
		}, this);

		Object.each(options.planes, function(edges, plane){

			var capitalized = plane.capitalize(),
				style = this.getStyle(plane);

			if (style == 'auto' && !dimensions) dimensions = this.getDimensions();

			style = styles[plane] = (style == 'auto') ? dimensions[plane] : style.toInt();
			size['total' + capitalized] = style;

			edges.each(function(edge){
				var edgesize = calculateEdgeSize(edge, styles);
				size['computed' + edge.capitalize()] = edgesize;
				size['total' + capitalized] += edgesize;
			});

		}, this);

		return Object.append(size, styles);
	}

});

}).call(this);


/*
---

script: Element.Position.js

name: Element.Position

description: Extends the Element native object to include methods useful positioning elements relative to others.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Element.Dimensions
  - /Element.Measure

provides: [Element.Position]

...
*/

(function(){

var original = Element.prototype.position;

Element.implement({

	position: function(options){
		//call original position if the options are x/y values
		if (options && (options.x != null || options.y != null)){
			return original ? original.apply(this, arguments) : this;
		}

		Object.each(options || {}, function(v, k){
			if (v == null) delete options[k];
		});

		options = Object.merge({
			// minimum: { x: 0, y: 0 },
			// maximum: { x: 0, y: 0},
			relativeTo: document.body,
			position: {
				x: 'center', //left, center, right
				y: 'center' //top, center, bottom
			},
			offset: {x: 0, y: 0}/*,
			edge: false,
			returnPos: false,
			relFixedPosition: false,
			ignoreMargins: false,
			ignoreScroll: false,
			allowNegative: false*/
		}, options);

		//compute the offset of the parent positioned element if this element is in one
		var parentOffset = {x: 0, y: 0},
			parentPositioned = false;

		/* dollar around getOffsetParent should not be necessary, but as it does not return
		 * a mootools extended element in IE, an error occurs on the call to expose. See:
		 * http://mootools.lighthouseapp.com/projects/2706/tickets/333-element-getoffsetparent-inconsistency-between-ie-and-other-browsers */
		var offsetParent = this.measure(function(){
			return document.id(this.getOffsetParent());
		});
		if (offsetParent && offsetParent != this.getDocument().body){
			parentOffset = offsetParent.measure(function(){
				return this.getPosition();
			});
			parentPositioned = offsetParent != document.id(options.relativeTo);
			options.offset.x = options.offset.x - parentOffset.x;
			options.offset.y = options.offset.y - parentOffset.y;
		}

		//upperRight, bottomRight, centerRight, upperLeft, bottomLeft, centerLeft
		//topRight, topLeft, centerTop, centerBottom, center
		var fixValue = function(option){
			if (typeOf(option) != 'string') return option;
			option = option.toLowerCase();
			var val = {};

			if (option.test('left')){
				val.x = 'left';
			} else if (option.test('right')){
				val.x = 'right';
			} else {
				val.x = 'center';
			}

			if (option.test('upper') || option.test('top')){
				val.y = 'top';
			} else if (option.test('bottom')){
				val.y = 'bottom';
			} else {
				val.y = 'center';
			}

			return val;
		};

		options.edge = fixValue(options.edge);
		options.position = fixValue(options.position);
		if (!options.edge){
			if (options.position.x == 'center' && options.position.y == 'center') options.edge = {x:'center', y:'center'};
			else options.edge = {x:'left', y:'top'};
		}

		this.setStyle('position', 'absolute');
		var rel = document.id(options.relativeTo) || document.body,
				calc = rel == document.body ? window.getScroll() : rel.getPosition(),
				top = calc.y, left = calc.x;

		var dim = this.getDimensions({
			computeSize: true,
			styles:['padding', 'border','margin']
		});

		var pos = {},
			prefY = options.offset.y,
			prefX = options.offset.x,
			winSize = window.getSize();

		switch (options.position.x){
			case 'left':
				pos.x = left + prefX;
				break;
			case 'right':
				pos.x = left + prefX + rel.offsetWidth;
				break;
			default: //center
				pos.x = left + ((rel == document.body ? winSize.x : rel.offsetWidth)/2) + prefX;
				break;
		}

		switch (options.position.y){
			case 'top':
				pos.y = top + prefY;
				break;
			case 'bottom':
				pos.y = top + prefY + rel.offsetHeight;
				break;
			default: //center
				pos.y = top + ((rel == document.body ? winSize.y : rel.offsetHeight)/2) + prefY;
				break;
		}

		if (options.edge){
			var edgeOffset = {};

			switch (options.edge.x){
				case 'left':
					edgeOffset.x = 0;
					break;
				case 'right':
					edgeOffset.x = -dim.x-dim.computedRight-dim.computedLeft;
					break;
				default: //center
					edgeOffset.x = -(dim.totalWidth/2);
					break;
			}

			switch (options.edge.y){
				case 'top':
					edgeOffset.y = 0;
					break;
				case 'bottom':
					edgeOffset.y = -dim.y-dim.computedTop-dim.computedBottom;
					break;
				default: //center
					edgeOffset.y = -(dim.totalHeight/2);
					break;
			}

			pos.x += edgeOffset.x;
			pos.y += edgeOffset.y;
		}

		pos = {
			left: ((pos.x >= 0 || parentPositioned || options.allowNegative) ? pos.x : 0).toInt(),
			top: ((pos.y >= 0 || parentPositioned || options.allowNegative) ? pos.y : 0).toInt()
		};

		var xy = {left: 'x', top: 'y'};

		['minimum', 'maximum'].each(function(minmax){
			['left', 'top'].each(function(lr){
				var val = options[minmax] ? options[minmax][xy[lr]] : null;
				if (val != null && ((minmax == 'minimum') ? pos[lr] < val : pos[lr] > val)) pos[lr] = val;
			});
		});

		if (rel.getStyle('position') == 'fixed' || options.relFixedPosition){
			var winScroll = window.getScroll();
			pos.top+= winScroll.y;
			pos.left+= winScroll.x;
		}
		if (options.ignoreScroll){
			var relScroll = rel.getScroll();
			pos.top -= relScroll.y;
			pos.left -= relScroll.x;
		}

		if (options.ignoreMargins){
			pos.left += (
				options.edge.x == 'right' ? dim['margin-right'] :
				options.edge.x == 'center' ? -dim['margin-left'] + ((dim['margin-right'] + dim['margin-left'])/2) :
					- dim['margin-left']
			);
			pos.top += (
				options.edge.y == 'bottom' ? dim['margin-bottom'] :
				options.edge.y == 'center' ? -dim['margin-top'] + ((dim['margin-bottom'] + dim['margin-top'])/2) :
					- dim['margin-top']
			);
		}

		pos.left = Math.ceil(pos.left);
		pos.top = Math.ceil(pos.top);
		if (options.returnPos) return pos;
		else this.setStyles(pos);
		return this;
	}

});

}).call(this);


/*
---

script: Class.Occlude.js

name: Class.Occlude

description: Prevents a class from being applied to a DOM element twice.

license: MIT-style license.

authors:
  - Aaron Newton

requires:
  - Core/Class
  - Core/Element
  - /MooTools.More

provides: [Class.Occlude]

...
*/

Class.Occlude = new Class({

	occlude: function(property, element){
		element = document.id(element || this.element);
		var instance = element.retrieve(property || this.property);
		if (instance && !this.occluded)
			return (this.occluded = instance);

		this.occluded = false;
		element.store(property || this.property, this);
		return this.occluded;
	}

});


/*
---

script: IframeShim.js

name: IframeShim

description: Defines IframeShim, a class for obscuring select lists and flash objects in IE.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Element.Event
  - Core/Element.Style
  - Core/Options
  - Core/Events
  - /Element.Position
  - /Class.Occlude

provides: [IframeShim]

...
*/

var IframeShim = new Class({

	Implements: [Options, Events, Class.Occlude],

	options: {
		className: 'iframeShim',
		src: 'javascript:false;document.write("");',
		display: false,
		zIndex: null,
		margin: 0,
		offset: {x: 0, y: 0},
		browsers: (Browser.ie6 || (Browser.firefox && Browser.version < 3 && Browser.Platform.mac))
	},

	property: 'IframeShim',

	initialize: function(element, options){
		this.element = document.id(element);
		if (this.occlude()) return this.occluded;
		this.setOptions(options);
		this.makeShim();
		return this;
	},

	makeShim: function(){
		if (this.options.browsers){
			var zIndex = this.element.getStyle('zIndex').toInt();

			if (!zIndex){
				zIndex = 1;
				var pos = this.element.getStyle('position');
				if (pos == 'static' || !pos) this.element.setStyle('position', 'relative');
				this.element.setStyle('zIndex', zIndex);
			}
			zIndex = ((this.options.zIndex != null || this.options.zIndex === 0) && zIndex > this.options.zIndex) ? this.options.zIndex : zIndex - 1;
			if (zIndex < 0) zIndex = 1;
			this.shim = new Element('iframe', {
				src: this.options.src,
				scrolling: 'no',
				frameborder: 0,
				styles: {
					zIndex: zIndex,
					position: 'absolute',
					border: 'none',
					filter: 'progid:DXImageTransform.Microsoft.Alpha(style=0,opacity=0)'
				},
				'class': this.options.className
			}).store('IframeShim', this);
			var inject = (function(){
				this.shim.inject(this.element, 'after');
				this[this.options.display ? 'show' : 'hide']();
				this.fireEvent('inject');
			}).bind(this);
			if (!IframeShim.ready) window.addEvent('load', inject);
			else inject();
		} else {
			this.position = this.hide = this.show = this.dispose = Function.from(this);
		}
	},

	position: function(){
		if (!IframeShim.ready || !this.shim) return this;
		var size = this.element.measure(function(){
			return this.getSize();
		});
		if (this.options.margin != undefined){
			size.x = size.x - (this.options.margin * 2);
			size.y = size.y - (this.options.margin * 2);
			this.options.offset.x += this.options.margin;
			this.options.offset.y += this.options.margin;
		}
		this.shim.set({width: size.x, height: size.y}).position({
			relativeTo: this.element,
			offset: this.options.offset
		});
		return this;
	},

	hide: function(){
		if (this.shim) this.shim.setStyle('display', 'none');
		return this;
	},

	show: function(){
		if (this.shim) this.shim.setStyle('display', 'block');
		return this.position();
	},

	dispose: function(){
		if (this.shim) this.shim.dispose();
		return this;
	},

	destroy: function(){
		if (this.shim) this.shim.destroy();
		return this;
	}

});

window.addEvent('load', function(){
	IframeShim.ready = true;
});


/*
---

script: Mask.js

name: Mask

description: Creates a mask element to cover another.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Options
  - Core/Events
  - Core/Element.Event
  - /Class.Binds
  - /Element.Position
  - /IframeShim

provides: [Mask]

...
*/

var Mask = new Class({

	Implements: [Options, Events],

	Binds: ['position'],

	options: {/*
		onShow: function(){},
		onHide: function(){},
		onDestroy: function(){},
		onClick: function(event){},
		inject: {
			where: 'after',
			target: null,
		},
		hideOnClick: false,
		id: null,
		destroyOnHide: false,*/
		style: {},
		'class': 'mask',
		maskMargins: false,
		useIframeShim: true,
		iframeShimOptions: {}
	},

	initialize: function(target, options){
		this.target = document.id(target) || document.id(document.body);
		this.target.store('mask', this);
		this.setOptions(options);
		this.render();
		this.inject();
	},

	render: function(){
		this.element = new Element('div', {
			'class': this.options['class'],
			id: this.options.id || 'mask-' + String.uniqueID(),
			styles: Object.merge({}, this.options.style, {
				display: 'none'
			}),
			events: {
				click: function(event){
					this.fireEvent('click', event);
					if (this.options.hideOnClick) this.hide();
				}.bind(this)
			}
		});

		this.hidden = true;
	},

	toElement: function(){
		return this.element;
	},

	inject: function(target, where){
		where = where || (this.options.inject ? this.options.inject.where : '') || this.target == document.body ? 'inside' : 'after';
		target = target || (this.options.inject && this.options.inject.target) || this.target;

		this.element.inject(target, where);

		if (this.options.useIframeShim){
			this.shim = new IframeShim(this.element, this.options.iframeShimOptions);

			this.addEvents({
				show: this.shim.show.bind(this.shim),
				hide: this.shim.hide.bind(this.shim),
				destroy: this.shim.destroy.bind(this.shim)
			});
		}
	},

	position: function(){
		this.resize(this.options.width, this.options.height);

		this.element.position({
			relativeTo: this.target,
			position: 'topLeft',
			ignoreMargins: !this.options.maskMargins,
			ignoreScroll: this.target == document.body
		});

		return this;
	},

	resize: function(x, y){
		var opt = {
			styles: ['padding', 'border']
		};
		if (this.options.maskMargins) opt.styles.push('margin');

		var dim = this.target.getComputedSize(opt);
		if (this.target == document.body){
			this.element.setStyles({width: 0, height: 0});
			var win = window.getScrollSize();
			if (dim.totalHeight < win.y) dim.totalHeight = win.y;
			if (dim.totalWidth < win.x) dim.totalWidth = win.x;
		}
		this.element.setStyles({
			width: Array.pick([x, dim.totalWidth, dim.x]),
			height: Array.pick([y, dim.totalHeight, dim.y])
		});

		return this;
	},

	show: function(){
		if (!this.hidden) return this;

		window.addEvent('resize', this.position);
		this.position();
		this.showMask.apply(this, arguments);

		return this;
	},

	showMask: function(){
		this.element.setStyle('display', 'block');
		this.hidden = false;
		this.fireEvent('show');
	},

	hide: function(){
		if (this.hidden) return this;

		window.removeEvent('resize', this.position);
		this.hideMask.apply(this, arguments);
		if (this.options.destroyOnHide) return this.destroy();

		return this;
	},

	hideMask: function(){
		this.element.setStyle('display', 'none');
		this.hidden = true;
		this.fireEvent('hide');
	},

	toggle: function(){
		this[this.hidden ? 'show' : 'hide']();
	},

	destroy: function(){
		this.hide();
		this.element.destroy();
		this.fireEvent('destroy');
		this.target.eliminate('mask');
	}

});

Element.Properties.mask = {

	set: function(options){
		var mask = this.retrieve('mask');
		if (mask) mask.destroy();
		return this.eliminate('mask').store('mask:options', options);
	},

	get: function(){
		var mask = this.retrieve('mask');
		if (!mask){
			mask = new Mask(this, this.retrieve('mask:options'));
			this.store('mask', mask);
		}
		return mask;
	}

};

Element.implement({

	mask: function(options){
		if (options) this.set('mask', options);
		this.get('mask').show();
		return this;
	},

	unmask: function(){
		this.get('mask').hide();
		return this;
	}

});


/*
---

script: Spinner.js

name: Spinner

description: Adds a semi-transparent overlay over a dom element with a spinnin ajax icon.

license: MIT-style license

authors:
  - Aaron Newton

requires:
  - Core/Fx.Tween
  - Core/Request
  - /Class.refactor
  - /Mask

provides: [Spinner]

...
*/

var Spinner = new Class({

	Extends: Mask,

	Implements: Chain,

	options: {/*
		message: false,*/
		'class': 'spinner',
		containerPosition: {},
		content: {
			'class': 'spinner-content'
		},
		messageContainer: {
			'class': 'spinner-msg'
		},
		img: {
			'class': 'spinner-img'
		},
		fxOptions: {
			link: 'chain'
		}
	},

	initialize: function(target, options){
		this.target = document.id(target) || document.id(document.body);
		this.target.store('spinner', this);
		this.setOptions(options);
		this.render();
		this.inject();

		// Add this to events for when noFx is true; parent methods handle hide/show.
		var deactivate = function(){ this.active = false; }.bind(this);
		this.addEvents({
			hide: deactivate,
			show: deactivate
		});
	},

	render: function(){
		this.parent();

		this.element.set('id', this.options.id || 'spinner-' + String.uniqueID());

		this.content = document.id(this.options.content) || new Element('div', this.options.content);
		this.content.inject(this.element);

		if (this.options.message){
			this.msg = document.id(this.options.message) || new Element('p', this.options.messageContainer).appendText(this.options.message);
			this.msg.inject(this.content);
		}

		if (this.options.img){
			this.img = document.id(this.options.img) || new Element('div', this.options.img);
			this.img.inject(this.content);
		}

		this.element.set('tween', this.options.fxOptions);
	},

	show: function(noFx){
		if (this.active) return this.chain(this.show.bind(this));
		if (!this.hidden){
			this.callChain.delay(20, this);
			return this;
		}

		this.active = true;

		return this.parent(noFx);
	},

	showMask: function(noFx){
		var pos = function(){
			this.content.position(Object.merge({
				relativeTo: this.element
			}, this.options.containerPosition));
		}.bind(this);

		if (noFx){
			this.parent();
			pos();
		} else {
			if (!this.options.style.opacity) this.options.style.opacity = this.element.getStyle('opacity').toFloat();
			this.element.setStyles({
				display: 'block',
				opacity: 0
			}).tween('opacity', this.options.style.opacity);
			pos();
			this.hidden = false;
			this.fireEvent('show');
			this.callChain();
		}
	},

	hide: function(noFx){
		if (this.active) return this.chain(this.hide.bind(this));
		if (this.hidden){
			this.callChain.delay(20, this);
			return this;
		}
		this.active = true;
		return this.parent(noFx);
	},

	hideMask: function(noFx){
		if (noFx) return this.parent();
		this.element.tween('opacity', 0).get('tween').chain(function(){
			this.element.setStyle('display', 'none');
			this.hidden = true;
			this.fireEvent('hide');
			this.callChain();
		}.bind(this));
	},

	destroy: function(){
		this.content.destroy();
		this.parent();
		this.target.eliminate('spinner');
	}

});

Request = Class.refactor(Request, {

	options: {
		useSpinner: false,
		spinnerOptions: {},
		spinnerTarget: false
	},

	initialize: function(options){
		this._send = this.send;
		this.send = function(options){
			var spinner = this.getSpinner();
			if (spinner) spinner.chain(this._send.pass(options, this)).show();
			else this._send(options);
			return this;
		};
		this.previous(options);
	},

	getSpinner: function(){
		if (!this.spinner){
			var update = document.id(this.options.spinnerTarget) || document.id(this.options.update);
			if (this.options.useSpinner && update){
				update.set('spinner', this.options.spinnerOptions);
				var spinner = this.spinner = update.get('spinner');
				['complete', 'exception', 'cancel'].each(function(event){
					this.addEvent(event, spinner.hide.bind(spinner));
				}, this);
			}
		}
		return this.spinner;
	}

});

Element.Properties.spinner = {

	set: function(options){
		var spinner = this.retrieve('spinner');
		if (spinner) spinner.destroy();
		return this.eliminate('spinner').store('spinner:options', options);
	},

	get: function(){
		var spinner = this.retrieve('spinner');
		if (!spinner){
			spinner = new Spinner(this, this.retrieve('spinner:options'));
			this.store('spinner', spinner);
		}
		return spinner;
	}

};

Element.implement({

	spin: function(options){
		if (options) this.set('spinner', options);
		this.get('spinner').show();
		return this;
	},

	unspin: function(){
		this.get('spinner').hide();
		return this;
	}

});

