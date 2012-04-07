var StatusBase = new Class({

	setup: function(statuses){
		var self = this;

		self.statuses = statuses;

	},

	get: function(id){
		return this.statuses.filter(function(status){
			return status.id == id
		}).pick()
	},

});
window.Status = new StatusBase();
