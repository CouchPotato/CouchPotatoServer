var BlockHeader = new Class({

	Extends: BlockNavigation,

	create: function(){
		var self = this,
			animation_options = {
				type: dynamics.spring
			},
			couch, potato;

		self.parent();

		self.el.adopt(
			self.logo = new Element('a.logo', {
				'href': App.createUrl(''),
				'events': {
					'mouseenter': function(){
						dynamics.animate(couch, {
							opacity: 0,
							translateX: -50
						}, animation_options);

						dynamics.animate(potato, {
							opacity: 1,
							translateX: 0
						}, animation_options);
					},
					'mouseleave': function(){
						dynamics.animate(couch, {
							opacity: 1,
							translateX: 0
						}, animation_options);

						dynamics.animate(potato, {
							opacity: 0,
							translateX: 50
						}, animation_options);
					}
				}
			}).adopt(
				couch = new Element('span[text=Couch]'),
				potato = new Element('span[text=Potato]')
			),
			self.nav
		);



	}

});
