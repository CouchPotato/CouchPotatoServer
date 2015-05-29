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
		var self = this;

		self.container = new Element('div.mask.question')
			.grab(self.inner = new Element('div.inner').adopt(
				new Element('h3', {
					'html': this.question
				}),
				new Element('div.hint', {
					'html': this.hint
				})
			)
		).inject(document.body);

		setTimeout(function(){
			self.container.addClass('show');
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

		// animate out
		self.container.removeClass('show');
	},

	toElement : function() {
		return this.container;
	}

});
