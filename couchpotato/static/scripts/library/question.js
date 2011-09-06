var Question = new Class( {

	initialize : function(question, hint, answers) {
		var self = this

		self.question = question
		self.hint = hint
		self.answers = answers

		self.createQuestion()
		self.answers.each(function(answer) {
			self.createAnswer(answer)
		})
		self.createMask()

	},

	createMask : function() {
		var self = this

		$(document.body).mask( {
			'hideOnClick' : true,
			'destroyOnHide' : true,
			'onHide' : function() {
				self.container.destroy();
			}
		}).show();
	},

	createQuestion : function() {

		this.container = new Element('div', {
			'class' : 'question'
		}).adopt(
			new Element('h3', {
				'html': this.question
			}),
			new Element('div.hint', {
				'html': this.hint
			})
		).inject(document.body)

		this.container.position( {
			'position' : 'center'
		});

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
					'onSuccess': function() {
						(options.onSuccess || function(){})()
						self.close();
					}
				})).send();	
			});
		}
	},

	close : function() {
		$(document.body).get('mask').destroy();
	},

	toElement : function() {
		return this.container
	}

})
