/*
---
description: Fill the empty space around elements, creating a spotlight effect.

license: GPL v3.0

authors:
- Ruud Burger

requires:
- core/1.3: [Class.Extras, Element.Dimensions]

provides: [Spotlight]

...
*/

var Spotlight = new Class({

	Implements: [Options],

	options: {
		'fillClass': 'spotlight_fill',
		'fillColor': [255,255,255],
		'fillOpacity': 1,
		'parent': null,
		'inject': null,
		'soften': 10
	},

	initialize: function(elements, options){
		var self = this;
		self.setOptions(options);

		self.setElements(elements);
		self.clean();

	},

	clean: function(){
		var self = this;

		self.range = []; self.fills = []; self.edges = [];

		self.vert = [];
		self.vert_el = [];

		self.top = []; self.left = [];
		self.width = []; self.height = [];
	},

	setElements: function(elements){
		this.elements = elements;
	},

	addElement: function(element){
		this.elements.include(element);
	},

	create: function(){
		var self = this;

		self.destroy();

		var page_c = $(self.options.parent || window).getScrollSize();
		var soften = self.options.soften;

		// Get the top and bottom of all the elements
		self.elements.each(function(el, nr){
			var c = el.getCoordinates();

			if(c.top > 0 && nr == 0){
				self.vert.append([0]);
				self.vert_el.append([null]);
			}

			// Top
			self.vert.append([c.top-soften]);
			self.vert_el.append([el]);

			// Bottom
			self.vert.append([c.top+c.height+soften]);
			self.vert_el.append([el]);

			// Add it to range, for later calculation from left to right
			self.range.append([{
				'el': el,
				'top': c.top-soften,
				'bottom': c.top+c.height+soften,
				'left': c.left-soften,
				'right': c.left+c.width+soften
			}])

			// Create soft edge around element
			self.soften(el);

		});

		if(self.elements.length == 0){
			self.vert.append([0]);
			self.vert_el.append([null]);
		}

		// Reorder
		var vert = self.vert.clone().sort(self.numberSort) // Use custom sort function because apparently 100 is less then 20..
			vert_el_new = [], vert_new = [];
		vert.each(function(v){
			var old_nr = self.vert.indexOf(v);
			vert_el_new.append([self.vert_el[old_nr]]);
			vert_new.append([v]);

		});
		self.vert = vert_new;
		self.vert_el = vert_el_new;

		// Shorten vars
		var vert = self.vert,
			vert_el = self.vert_el;
		var t, h, l, w, left, width,
			row_el, cursor = 0;

		// Loop over all vertical lines
		vert.each(function(v, nr){

			// Use defaults if el == null (for first fillblock)
			var c = vert_el[nr] ? vert_el[nr].getCoordinates() : {
				'left': 0,
				'top': 0,
				'width': page_c.x,
				'height': 0
			};

			// Loop till cursor gets to parent_element.width
			var fail_safe = 0;
			while (cursor < page_c.x && fail_safe < 10){

				t = vert[nr]; // Top is the same for every element in a row
				h = (nr == vert.length-1) ? (page_c.y - t) : vert[nr+1] - vert[nr]; // So is hight

				// First element get special treatment
				if(nr == 0){
					l = 0;
					w = c.width+(2*soften);
					cursor += w;
				}
				else {

					row_el = self.firstFromLeft(cursor, t) // First next element
					left = row_el.el ? row_el.left : c.left-soften;
					width = row_el.el ? row_el.left - cursor : c.left-soften;

					if(t == c.bottom+soften && !row_el.el)
						width = page_c.x;

					l = cursor;
					if(cursor < left){
						w = width;
						cursor += w+(row_el.right - row_el.left);
					}
					else {
						w = page_c.x-l;
						cursor += w;
					}

				}

				// Add it to the pile!
				if(h > 0 && w > 0){
					self.top.append([t]); self.left.append([l]);
					self.width.append([w]); self.height.append([h]);
				}

				fail_safe++;

			}

			cursor = 0; // New line, reset cursor position
			fail_safe = 0;

		});

		// Create the fill blocks
		self.top.each(self.createFillItem.bind(self));

	},

	createFillItem: function(top, nr){
		var self = this;

		var fill = new Element('div', {
			'class': self.options.fillClass,
			'styles': {
				'position': 'absolute',
				'background-color': 'rgba('+self.options.fillColor.join(',')+', '+self.options.fillOpacity+')',
				'display': 'block',
				'z-index': 2,
				'top': self.top[nr],
				'left': self.left[nr],
				'height': self.height[nr],
				'width': self.width[nr]
			}
		}).inject(self.options.inject || document.body);

		self.fills.include(fill);
	},

	// Find the first element after x,y coordinates
	firstFromLeft: function(x, y){
		var self = this;

		var lowest_left = null;
		var return_data = {};

		self.range.each(function(range){
			var is_within_height_range = range.top <= y && range.bottom > y,
				is_within_width_range = range.left >= x,
				more_left_then_previous = range.left < lowest_left || lowest_left == null;

			if(is_within_height_range && is_within_width_range && more_left_then_previous){
				lowest_left = range.left;
				return_data = range;
			}
		})

		return return_data

	},

	soften: function(el){
		var self = this;
		var soften = self.options.soften;

		var c = el.getCoordinates();
		var from_color = 'rgba('+self.options.fillColor.join(',')+', '+self.options.fillOpacity+')';
		var to_color = 'rgba('+self.options.fillColor.join(',')+', 0)';

		// Top
		self.createEdge({
			'top': c.top-soften,
			'left': c.left-soften,
			'width': c.width+(2*soften),
			'background': '-webkit-gradient(linear, left top, left bottom, from('+from_color+'), to('+to_color+'))',
			'background': '-moz-linear-gradient(top, '+from_color+', '+to_color+')'
		})

		// Right
		self.createEdge({
			'top': c.top-soften,
			'left': c.right,
			'height': c.height+(2*soften),
			'background': '-webkit-gradient(linear, left, right, from('+from_color+'), to('+to_color+'))',
			'background': '-moz-linear-gradient(right, '+from_color+', '+to_color+')'
		})

		// Bottom
		self.createEdge({
			'top': c.bottom,
			'left': c.left-soften,
			'width': c.width+(2*soften),
			'background': '-webkit-gradient(linear, left bottom, left top, from('+from_color+'), to('+to_color+'))',
			'background': '-moz-linear-gradient(bottom, '+from_color+', '+to_color+')'
		})

		// Left
		self.createEdge({
			'top': c.top-soften,
			'left': c.left-soften,
			'height': c.height+(2*soften),
			'background': '-webkit-gradient(linear, right, left, from('+from_color+'), to('+to_color+'))',
			'background': '-moz-linear-gradient(left, '+from_color+', '+to_color+')'
		})

	},
	
	createEdge: function(style){
		var self = this;

		var soften = self.options.soften;
		var edge = new Element('div', {
			'styles': Object.merge({
				'position': 'absolute',
				'width': soften,
				'height': soften,
			}, style)
		}).inject(self.options.inject || document.body)
		
		self.edges.include(edge);
		
	},

	destroy: function(){
		var self = this;
		self.fills.each(function(fill){
			fill.destroy();
		})
		self.edges.each(function(edge){
			edge.destroy();
		})
		self.clean();
	},

	numberSort: function (a, b) {
		return a - b;
	}

});