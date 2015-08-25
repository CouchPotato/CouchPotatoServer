/*
---
description:     ScrollSpy

authors:
  - David Walsh (http://davidwalsh.name)

license:
  - MIT-style license

requires:
  core/1.2.1:   '*'

provides:
  - ScrollSpy
...
*/
var ScrollSpy = new Class({

	/* implements */
	Implements: [Options,Events],

	/* options */
	options: {
		container: window,
		max: 0,
		min: 0,
		mode: 'vertical'/*,
		onEnter: $empty,
		onLeave: $empty,
		onScroll: $empty,
		onTick: $empty
		*/
	},

	/* initialization */
	initialize: function(options) {
		/* set options */
		this.setOptions(options);
		this.container = document.id(this.options.container);
		this.enters = this.leaves = 0;
		this.inside = false;

		/* listener */
		var self = this;
		this.listener = function(e) {
			/* if it has reached the level */
			var position = self.container.getScroll(),
				xy = position[self.options.mode == 'vertical' ? 'y' : 'x'],
				min = typeOf(self.options.min) == 'function' ? self.options.min() : self.options.min,
				max = typeOf(self.options.max) == 'function' ? self.options.max() : self.options.max;

			if(xy >= min && (max === 0 || xy <= max)) {
					/* trigger enter event if necessary */
					if(!self.inside) {
						/* record as inside */
						self.inside = true;
						self.enters++;
						/* fire enter event */
						self.fireEvent('enter',[position,self.enters,e]);
					}
					/* trigger the "tick", always */
					self.fireEvent('tick',[position,self.inside,self.enters,self.leaves,e]);
			}
			/* trigger leave */
			else if(self.inside){
				self.inside = false;
				self.leaves++;
				self.fireEvent('leave',[position,self.leaves,e]);
			}
			/* fire scroll event */
			self.fireEvent('scroll',[position,self.inside,self.enters,self.leaves,e]);
		};

		/* make it happen */
		this.addListener();
	},

	/* starts the listener */
	start: function() {
		this.container.addEvent('scroll',this.listener);
	},

	/* stops the listener */
	stop: function() {
		this.container.removeEvent('scroll',this.listener);
	},

	/* legacy */
	addListener: function() {
		this.start();
	}
});
