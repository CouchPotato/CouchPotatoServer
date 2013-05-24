var Question = new Class( {

	initialize : function(question, hint, answers) {
		var self = this

		self.question = question
		self.hint = hint
		self.answers = answers

		self.createQuestion();
		self.answers.each(function(answer) {
			self.createAnswer(answer)
		})

	},

	createQuestion : function() {
		var self = this;

		self.container = new Element('div.mask.question').adopt(
			new Element('h3', {
				'html': this.question
			}),
			new Element('div.hint', {
				'html': this.hint
			})
		).fade('hide').inject(document.body).fade('in')

	},

	createAnswer : function(options) {
		var self = this

		var answer = new Element('a', Object.merge(options, {
			'class' : 'answer button '+(options['class'] || '')+(options['cancel'] ? ' cancel' : '')
		})).inject(this.container)

		if (options.cancel) {
			answer.addEvent('click', self.close.bind(self))
		}
		else if (options.request) {
			answer.addEvent('click', function(e){
				e.stop();
				new Request(Object.merge(options, {
					'url': options.href,
					'onComplete': function() {
						(options.onComplete || function(){})()
						self.close();
					}
				})).send();
			});
		}
	},

	close : function() {
		var self = this;
		self.container.fade('out');
		(function(){self.container.destroy()}).delay(1000);
	},

	toElement : function() {
		return this.container
	}

})
