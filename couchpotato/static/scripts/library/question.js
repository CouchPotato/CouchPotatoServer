var Question = new Class( {

	initialize : function(question, hint, answers) {
		var self = this;

		self.question = question;
		self.hint = hint;
		self.answers = answers;

		self.createQuestion();
		self.answers.each(function(answer) {
			self.createAnswer(answer);
		});

	},

	createQuestion : function() {
		var self = this,
			h3, hint;

		self.container = new Element('div.mask.question')
			.grab(self.inner = new Element('div.inner').adopt(
				h3 = new Element('h3', {
					'html': this.question
				}),
				hint = this.hint ? new Element('div.hint', {
					'html': this.hint
				}) : null
			)
		).inject(document.body);

		requestTimeout(function(){
			self.container.addClass('show');

			self.inner.getElements('> *').each(function(el, nr){
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
					delay: 400 + (nr * 100)
				});
			});
		}, 10);

	},

	createAnswer : function(options) {
		var self = this;

		var answer = new Element('a', Object.merge(options, {
			'class' : 'answer button '+(options['class'] || '')+(options.cancel ? ' cancel' : '')
		})).inject(this.inner);

		if (options.cancel) {
			answer.addEvent('click', self.close.bind(self));
		}
		else if (options.request) {
			answer.addEvent('click', function(e){
				e.stop();
				new Request(Object.merge(options, {
					'url': options.href,
					'onComplete': function() {
						(options.onComplete || function(){})();
						self.close();
					}
				})).send();
			});
		}
	},

	close : function() {
		var self = this;

		var ended = function() {
			self.container.dispose();
			self.container.removeEventListener('transitionend', ended);
		};
		self.container.addEventListener('transitionend', ended, false);

		// Hide items
		self.inner.getElements('> *').reverse().each(function(el, nr){
			dynamics.css(el, {
				opacity: 1,
				translateY: 0
			});

			dynamics.animate(el, {
				opacity: 0,
				translateY: 50
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

		// animate out
		dynamics.setTimeout(function(){
			self.container.removeClass('show');
		}, 200);
	},

	toElement : function() {
		return this.container;
	}

});
