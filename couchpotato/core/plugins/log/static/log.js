Page.Log = new Class({

	Extends: PageBase,

	order: 60,
	name: 'log',
	title: 'Show recent logs.',
	has_tab: false,

	log_items: [],
	report_text: '\
### Steps to reproduce:\n\
1. ..\n\
2. ..\n\
\n\
### Information:\n\
Movie(s) I have this with: ...\n\
Quality of the movie being searched: ...\n\
Providers I use: ...\n\
Version of CouchPotato: {version}\n\
Running on: ...\n\
\n\
### Logs:\n\
```\n{issue}```',

	indexAction: function () {
		var self = this;

		self.getLogs(0);

	},

	getLogs: function (nr) {
		var self = this;

		if (self.log) self.log.destroy();
		self.log = new Element('div.container.loading', {
			'text': 'loading...',
			'events': {
				'mouseup:relay(.time)': function(e){
					self.showSelectionButton.delay(100, self, e);
				}
			}
		}).inject(self.el);

		Api.request('logging.get', {
			'data': {
				'nr': nr
			},
			'onComplete': function (json) {
				self.log.set('text', '');
				self.log_items = self.createLogElements(json.log);
				self.log.adopt(self.log_items);
				self.log.removeClass('loading');

				var nav = new Element('ul.nav', {
					'events': {
						'click:relay(li.select)': function (e, el) {
							self.getLogs(parseInt(el.get('text')) - 1);
						}
					}
				});

				// Type selection
				new Element('li.filter').grab(
					new Element('select', {
						'events': {
							'change': function () {
								var type_filter = this.getSelected()[0].get('value');
								self.el.set('data-filter', type_filter);
								self.scrollToBottom();
							}
						}
					}).adopt(
						new Element('option', {'value': 'ALL', 'text': 'Show all logs'}),
						new Element('option', {'value': 'INFO', 'text': 'Show only INFO'}),
						new Element('option', {'value': 'DEBUG', 'text': 'Show only DEBUG'}),
						new Element('option', {'value': 'ERROR', 'text': 'Show only ERROR'})
					)
				).inject(nav);

				// Selections
				for (var i = 0; i <= json.total; i++) {
					new Element('li', {
						'text': i + 1,
						'class': 'select ' + (nr == i ? 'active' : '')
					}).inject(nav);
				}

				// Clear button
				new Element('li.clear', {
					'text': 'clear',
					'events': {
						'click': function () {
							Api.request('logging.clear', {
								'onComplete': function () {
									self.getLogs(0);
								}
							});

						}
					}
				}).inject(nav);

				// Hint
				new Element('li.hint', {
					'text': 'Select multiple lines & report an issue'
				}).inject(nav);

				// Add to page
				nav.inject(self.log, 'top');

				self.scrollToBottom();
			}
		});

	},

	createLogElements: function (logs) {

		var elements = [];

		logs.each(function (log) {
			elements.include(new Element('div', {
				'class': 'time ' + log.type.toLowerCase()
			}).adopt(
				new Element('span', {
					'text': log.time
				}),
				new Element('span.type', {
					'text': log.type
				}),
				new Element('span.message', {
					'text': log.message
				})
			))
		});

		return elements;
	},

	scrollToBottom: function () {
		new Fx.Scroll(window, {'duration': 0}).toBottom();
	},

	showSelectionButton: function(e){
		var self = this,
			selection = self.getSelected(),
			start_node = selection.anchorNode,
			parent_start = start_node.parentNode.getParent('.time'),
			end_node = selection.focusNode.parentNode.getParent('.time'),
			text = '';

		var remove_button = function(){
			self.log.getElements('.highlight').removeClass('highlight');
			if(self.do_report)
				self.do_report.destroy();
			document.body.removeEvent('click', remove_button);
		};
		remove_button();

		if(parent_start)
			start_node = parent_start;

		var index = {
				'start': self.log_items.indexOf(start_node),
				'end': self.log_items.indexOf(end_node)
			};

		if(index.start > index.end){
			index = {
				'start': index.end,
				'end': index.start
			};
		}

		var nodes = self.log_items.slice(index.start, index.end + 1);

		nodes.each(function(node, nr){
			node.addClass('highlight');
			node.getElements('span').each(function(span){
				text += self.spaceFill(span.get('text') + ' ', 6);
			});
			text += '\n';
		});

		self.do_report = new Element('a.do_report.button', {
			'text': 'Report issue',
			'styles': {
				'top': e.page.y,
				'left': e.page.x
			},
			'events': {
				'click': function(e){
					(e).stop();

					self.showReport(text);
				}
			}
		}).inject(document.body);

		setTimeout(function(){
			document.body.addEvent('click', remove_button);
		}, 0);

	},

	showReport: function(text){
		var self = this,
			version = Updater.getInfo(),
			body = self.report_text
				.replace('{issue}', text)
				.replace('{version}', version ? version.version.repr : '...'),
			textarea;

		var overlay = new Element('div.report', {
			'method': 'post',
			'events': {
				'click': function(e){
					overlay.destroy();
				}
			}
		}).grab(
			new Element('div.bug', {
				'events': {
					'click': function(e){
						(e).stopPropagation();
					}
				}
			}).adopt(
				new Element('h1', {
					'text': 'Report a bug'
				}),
				new Element('span').adopt(
					new Element('span', {
						'text': 'Read '
					}),
					new Element('a.button', {
						'target': '_blank',
						'text': 'the contributing guide',
						'href': 'https://github.com/RuudBurger/CouchPotatoServer/blob/develop/contributing.md'
					}),
					new Element('span', {
						'text': ' before posting, then copy the text below'
					})
				),
				textarea = new Element('textarea', {
					'text': body,
					'events': {
						'click': function(){
							this.select();
						}
					}
				}),
				new Element('a.button', {
					'target': '_blank',
					'text': 'Create a new issue on GitHub with the text above',
					'href': 'https://github.com/RuudBurger/CouchPotatoServer/issues/new',
					'events': {
						'click': function(e){
							(e).stop();

							var body = textarea.get('value'),
								bdy = '?body=' + (body.length < 2000 ? encodeURIComponent(body) : 'Paste the text here'),
								win = window.open(e.target.get('href') + bdy, '_blank');
							win.focus();
						}
					}
				})
			)
		);

		overlay.inject(self.log);
	},

	getSelected: function(){
		if (window.getSelection)
			return window.getSelection();
		else if (document.getSelection)
			return document.getSelection();
		else {
			var selection = document.selection && document.selection.createRange();
			if (selection.text)
				return selection.text;
		}
		return false;

	},

	spaceFill: function( number, width ){
		if ( number.toString().length >= width )
			return number;
		return ( new Array( width ).join( ' ' ) + number.toString() ).substr( -width );
	}

});
