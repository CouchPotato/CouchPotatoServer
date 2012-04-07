var includes = {{includes|tojson}};
var excludes = {{excludes|tojson}};

var specialChars = '\\{}+.():-|^$';
var makeRegex = function(pattern) {
	pattern = pattern.split('');
	var i, len = pattern.length;
	for( i = 0; i < len; i++) {
		var character = pattern[i];
		if(specialChars.indexOf(character) > -1) {
			pattern[i] = '\\' + character;
		} else if(character === '?') {
			pattern[i] = '.';
		} else if(character === '*') {
			pattern[i] = '.*';
		}
	}
	return new RegExp('^' + pattern.join('') + '$');
};

var isCorrectUrl = function() {
	for(i in includes) {
		var reg = includes[i]
		if (makeRegex(reg).test(document.location.href))
			return true;
	}
	return false;
}
var addUserscript = function() {
	// Add window param
	document.body.setAttribute('cp_auto_open', true)

	// Load userscript
	var e = document.createElement('script');
	e.setAttribute('type', 'text/javascript');
	e.setAttribute('charset', 'UTF-8');
	e.setAttribute('src', '{{host}}couchpotato.js?r=' + Math.random() * 99999999);
	document.body.appendChild(e)
}
if(isCorrectUrl())
	addUserscript()
else
	alert('Can\'t find a proper movie on this page..')
