/*
---
description: Templated is a MooTools mixin class which creates elements for classes using a string-based HTML template which may included embedded attach points and events.

license: MIT-style

authors:
- David Walsh

requires:
- core/1.3: '*'

provides: [Templated]

...
*/

// Create scope limiter
(function(scope) {
	
	// Create some vars for strings
	// This will save bytes when compressed
	var strData = "data",
		strWidget = "widget",
		strAttach = "attach",
		dataWidgetType = strData + "-" + strWidget + "-type",
		dataWidgetProps = strData + "-" + strWidget + "-props",
		dataWidgetAttachPoint = strData + "-" + strWidget + "-" + strAttach + "-point",
		dataWidgetAttachEvent = strData + "-" + strWidget + "-" + strAttach + "-event",
		dataWidgetized = strData + "-widgetized";
	
	// Templated is a mixin for UI widgets
	scope.Templated = new Class({

		// The usual options object
		options: {
			// The default template
			template: "<div></div>",

			// The URL to get the template from *instead* of the string
			templateUrl: "",

			// A node reference for where this UI widget will be placed...in reference to
			element: null,

			// Should this widget be parsed for sub-widgets?
			widgetsInTemplate: true,

			// Property mappings (should be an object)
			// These override defaults
			propertyMappings: null,

			// Default property mappings
			// Thse properties on the element will be moved to the respective nodes within the template
			defaultPropertyMappings: null,

			// Should messages be debug to the console
			debugMode: true
		},
		
		// Create placeholders for attached points and events
		_attachPoints: [],
		_attachEvents: [],

		// Parse
		parse: function() {
				
			// Get shortcuts to the options and element
			var options = this.options,
				nodeRef = options.element = options.element || new Element("div").inject(document.body);
			
			// *IF* a templateUrl is specified, can't do anything until template is loaded
			// Defer parsing until we've got it
			if(options.templateUrl && Templated.templates && !Templated.templates[options.templateUrl]) {
				this.debug("[Templated:parse] Need to load template from URL:  " + options.templateUrl);
				this.getTemplate();
				return false;
			}

			// If already data-widgetized...gtfo
			if(nodeRef.retrieve("widget")) {
				this.debug("[Templated:parse] Node already widgetized, leaving ", nodeRef);
				return nodeRef.domNode;
			}

			// Mix noderef properties with options
			options.defaultPropertyMappings = options.defaultPropertyMappings || { // THESE OVERRIDE CLASSES IN THE TEMPLATE!!!!
				"id": "domNode",
				"style": "domNode",
				"class": "domNode"
			};
			Object.merge(options, this.getNodeProps(nodeRef));

			// postMixInProperties runs after options have been mixed with defaults but before
			// any templating is done
			this.postMixInProperties();
			
			// Build rendering - creates the actual nodes, attachpoints, and attachevents
			this.buildRendering();

			// Fire the "postCreate" method, which runs after nodes are created *but* before the nodes are rendered to the page
			this.postCreate();

			// Cleanup creation
			this.cleanupCreation();

			// "Startup": The widget is in the DOM and the widget is ready to go
			this.startup();

			// Return the domNode
			this.debug("[Templated:parse] At the end of parse, this is: ", this);
			return this.domNode;
		},
		
		// Creates build rendering
		buildRendering: function() {
			// Get shortcuts to the options and element
			var options = this.options, nodeRef = options.element;

			// Do string substitution on the template
			var template = this.template = options.template.substitute(options || {});

			// Create the DOM node within a DIV that's not rendered to the page
			var bitchNode = this.bitchNode = new Element("div", { html: template.trim() }),
				domNode = this.domNode = document.id(bitchNode.childNodes[0]);

			// Look for subwidgets if told to...
			if(options.widgetsInTemplate) {
				this.debug("[Templated:parse]  Looking for subwidgets under domNode", domNode);
				this.makeSubWidgets(this.domNode);
			}

			// Create the attachpoints for me, then my kiddies
			this.makeAttachPoints(domNode);
			if(options.widgetsInTemplate) domNode.getElements("[" + dataWidgetAttachPoint + "]").each(this.makeAttachPoints, this);
			this.debug("[Templated:parse]  Creating attachpoints", this._attachPoints);

			// Create the attachevents for me, then my kiddies
			this.makeAttachEvents(domNode);
			if(options.widgetsInTemplate) domNode.getElements("[" + dataWidgetAttachEvent + "]").each(this.makeAttachEvents, this);
			this.debug("Creating attachevents", this._attachEvents);

			// Map properties to nodes within the template
			// Mix the custom mappings with the default
			// This needs to happen after attachpoints
			var mappings = options.propertyMappings ? Object.merge(options.defaultPropertyMappings, options.propertyMappings) : options.defaultPropertyMappings;
			Object.each(mappings, function(value, key) {
				// Ignore the value if not present in the object
				if(!this[value]) return;
				// Assign the value to the key
				var currentProp = nodeRef.get(key);
				if(currentProp != "") this[value].set(key, currentProp);
			}.bind(this));

			// If this widget has a "containerNode", grab it's childNodes *or* inject innerHTML
			if(this.containerNode) {
				var kids = nodeRef.childNodes;
				kids.length ? $$(kids).inject(this.containerNode) : this.containerNode.set("html", nodeRef.get("html"));
			}
		},

		// "postMixInProperties" -- Fired after options have been mixed in
		postMixInProperties: function() {
			this.debug("[Templated:postMixInProperties] postMixInProperties!");
		},

		// "PostCreate" -- Fired after nodes are created, attachpoints and events are found
		postCreate: function() {
			this.debug("[Templated:postCreate] postCreate!");
		},
		
		// "CleanupCreation" -- Removes the old element, destroys bitch node
		cleanupCreation: function() {
			// Get hold of the dom node and bitch nodes
			var domNode = this.domNode, bitchNode = this.bitchNode, nodeRef = this.options.element;

			// Put the domNode where it should go and destroy the node reference
			domNode.replaces(nodeRef);
			nodeRef.destroy();

			// Mark as data-widgetized and store the widget within data
			domNode.set(dataWidgetized, true);
			domNode.store("widget", this);
			
			// Remove the bitch node
			bitchNode.destroy();
		},

		// "StartUp" -- Fired when node is in place
		startup: function(){
			this.debug("[Templated:startup] startup!");
		},

		// Focus on focus node, if present
		focus: function() { 
			var node = this.focusNode;
			node && node.focus();
		},

		// Create subwidgets from this
		makeSubWidgets: function(domNode) {
			if(!domNode) domNode = this.domNode;
			domNode.getElements("["+ dataWidgetType +"]:not([" + dataWidgetized + "])").each(function(node){
				// Store the subwidget's attachpoints, attachevents, class type, and properties
				var points = node.get(dataWidgetAttachPoint),
					events = node.get(dataWidgetAttachEvent),
					widgetProps = this.getNodeProps(node),
					klass = node.get(dataWidgetType).trim();

				// Create the widget
				if(scope[klass]) {
					var widget = new scope[klass](Object.merge(widgetProps, { element: node }));
					this.debug("[parse:makeSubWidgets]  Creating child widget: ", klass, widget);
					// Get access to its dom node
					widgetDomNode = widget.domNode;
					// Add attachments back to the widget
					points && widgetDomNode.set(dataWidgetAttachPoint, points.trim());
					events && widgetDomNode.set(dataWidgetAttachEvent, events.trim());
				}
			}, this);
		},

		// Makes attachpoints
		makeAttachPoints: function(node) {
			var points = node.get(dataWidgetAttachPoint);
			if(points) {
				points.trim().split(",").each(function(attach) {
					attach = attach.trim();
					this[attach] = node.retrieve("widget") || node;
					this.debug("[Templated:makeAttachPoints] " + attach, node);
					this._attachPoints.push({ node: node, name: attach });
				}, this);
				node.set(dataWidgetAttachPoint, "");
				node.set("data-widgetized-attach-point", points);
			}
		},

		// Makes attachevents
		makeAttachEvents: function(node) {
			// Temporarily store this widget's events so they may be added to this.domNode later
			var events = node.get(dataWidgetAttachEvent);
			// If there are events....
			if(events) {
				// For every event found....
				events.trim().split(",").each(function(event) {
					// Trim the event
					event = event.trim();
					// Split the event:method pair
					var eventFn = event.split(":");
					// Trim and rename each piece
					var nativeEvent = eventFn[0].trim(),
						classEvent = eventFn[1].trim();
					this.debug("[Templated:makeAttachEvents] " + nativeEvent + " / " + classEvent,node);
					
					// If the method isn't found on this, create a stub for it'
					if(!this[classEvent]) {
						this.debug("cant find ", classEvent, " in: ", this, " creating sub for it");
						this[classEvent] = function(){};
					}
					
					// Bind "this" to the event
					var ev = this[classEvent].bind(this);
					
					// Add the event to the domNode
					node.addEvent(nativeEvent, ev);
					
					// Store the event
					this._attachEvents.push({ type: nativeEvent, event: ev, node: node });
				}, this);
				
				// Remove the event from its former place and add to -ized data item
				var set = {
					"data-widgetized-attach-event": events
				};
				set[dataWidgetAttachEvent] = "";
				node.set(set);
				//node.set("data-widget-attach-event","");
				//node.set("data-widgetized-attach-event",events);
			}
		},

		// Destroy: removes node events
		destroy: function() {
			// Get reference to domNode
			var domNode = this.domNode, events = this._attachEvents, points = this._attachPoints;
			
			// Clear out children
			domNode.getElements("[" + dataWidgetized + "]").each(function(widget) {
				widget.destroy();
			});

			// Remove events
			if(events.length) {
				events.each(function(event) {
					if(event.node) event.node.removeEvents();
				});
			}
			// Remove node connections
			if(points.length) {
				points.each(function(point) {
					if(point.name != "domNode") this[point.name] = null;
				}, this);
			}
			// Destroy the dom node and its children, fin
			domNode.store("widget", null).destroy();
		},

		// Gets the in-node properties for a widget
		getNodeProps: function(node) {
			var props = node.get(dataWidgetProps),
				widgetProps = {};
			// Create the widget
			if(props) {
				// Not using JSON.parse because it's too restricting, especially with quotes
				var json = "{" + props.trim() + "}";
				if(JSON && JSON.decode) { // MooTools
					widgetProps = JSON.decode(json);
				}
				else { // Native
					eval("widgetProps = " + json);
				}
			}
			return widgetProps;
		},

		debug: function(one, two, three, four) {
			if(this.options.debugMode && console && console.log) {
				console.log("[" + (this.domNode ? this.domNode.id : "") + "]  ", one, two || "", three || "", four || "");
			}
		}
	});

	// If Request is available....
	if(Request) {
		Templated.templates = {};
		// Return the template
		Templated.implement({
			// Method to return cached template or retrieve new one synchronously
			getTemplate: function() {
				/*
				var url = this.options.templateUrl;
				// Try to return cached first
				if(Templated.templates[url]) {
					return Templated.templates[url];
				}
				else {
					// Send a new request
					return new Request({
						url: url,
						async: false, // Used to ensure that necessary templates are there
						onSuccess: function(template) {
							this.options.template = template;
							Templated.templates[url] = template;
							this.parse();
						}.bind(this)
					}).send();
				}
				*/
				
				var url = this.options.templateUrl;
				// Try to return cached first
				if(!Templated.templates[url]) {
					// Send a new request
					return new Request({
						url: url,
						async: false, // Used to ensure that necessary templates are there
						onSuccess: function(template) {
							this.options.template = template;
							Templated.templates[url] = template;
							this.parse();
						}.bind(this),
						onFailure: function() {
							Templated.templates[url] = Templated.prototype.options.template;
						}
					}).send();
				}
				return Templated.templates[url];
			}
		});
	}

	// Allow for parsing of an element and its children
	Element.implement({
		parse: function() {
			
			var elFn = function(element) {
				// Get the widget type
				var klass = element.get(dataWidgetType);
				// If the class exists....
				if(klass && scope[klass]) {
					// Create the new class instance
					new scope[klass]({ element: element });
				}
				else {
					window.console && console.log && console.log("klass does not exist!  ", klass);
				}
			};
			
			// Grab this and all nodes which are not already widgetized
			elFn(this);
			$$(this.getElements("["+ dataWidgetType +"]:not(" + dataWidgetized + ")")).each(elFn);
		}
	});

	// Get widget from id
	document.widget = function(idOrNode) {
		return document.id(idOrNode).retrieve("widget") || null;
	};
	
	
})(this); // Scope limiter