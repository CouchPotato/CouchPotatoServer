var Uniform = new Class({
	Implements : [Options],

	options : {
		focusedClass : 'focused',
		holderClass : 'ctrlHolder'
	},

	initialize : function(options) {
		this.setOptions(options);

		var focused = this.options.focusedClass;
		var holder = '.' + this.options.holderClass;

		$(document.body).addEvents( {
			'focus:relay(input, select, textarea)' : function() {
				var parent = this.getParent(holder);
				if (parent)
					parent.addClass(focused);
			},
			'blur:relay(input, select, textarea)' : function() {
				var parent = this.getParent(holder);
				if (parent)
					parent.removeClass(focused);
			}
		});
	}
});