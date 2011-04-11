var StatusBase = new Class({

	setup: function(statuses){
		var self = this;

		self.statuses = statuses;

	}

});
window.Status = new StatusBase();
