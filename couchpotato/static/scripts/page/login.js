window.addEvent('domready', function(){
	var b = $(document.body),
		login_page = b.hasClass('login');

	if(login_page){

		var form = b.getElement('form'),
			els = b.getElements('h1, .username, .password, .remember_me, .button');
		els.each(function(el, nr){

			dynamics.css(el, {
				opacity: 0,
				translateY: 50
			});

			dynamics.animate(el, {
				opacity: 1,
				translateY: 0
			}, {
				type: dynamics.spring,
				frequency: 200,
				friction: 300,
				duration: 800,
				anticipationSize: 175,
				anticipationStrength: 400,
				delay: nr * 100
			});

		});
	}
});
