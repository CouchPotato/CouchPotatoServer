// ==UserScript==
// @name        CouchPotato UserScript
// @description Add movies like a real CouchPotato
// @version     {{version}}

// @match       {{host}}*
{% for include in includes %}
// @match       {{include}}{% endfor %}
{% for exclude in excludes %}
// @exclude     {{exclude}}{% endfor %}
// @exclude     {{host}}{{api.rstrip('/')}}*

// ==/UserScript==

if (window.top == window.self){  // Only run on top window

var version = {{version}},
    host = '{{host}}',
    api = '{{api}}';

function create() {
    switch (arguments.length) {
    case 1:
        var A = document.createTextNode(arguments[0]);
        break;
    default:
        var A = document.createElement(arguments[0]), B = arguments[1];
        for ( var b in B) {
            if (b.indexOf("on") == 0){
                A.addEventListener(b.substring(2), B[b], false);
            }
            else if (",style,accesskey,id,name,src,href,which".indexOf(","
                    + b.toLowerCase()) != -1){
                A.setAttribute(b, B[b]);
            }
            else{
                A[b] = B[b];
            }
        }
        for ( var i = 2, len = arguments.length; i < len; ++i){
            A.appendChild(arguments[i]);
        }
    }
    return A;
}

if (typeof GM_addStyle == 'undefined'){
    GM_addStyle = function(css) {
        var head = document.getElementsByTagName('head')[0],
            style = document.createElement('style');
        if (!head)
            return;

        style.type = 'text/css';
        style.textContent = css;
        head.appendChild(style);
    }
}

// Styles
GM_addStyle('\
    #cp_popup { font-family: "Helvetica Neue", Helvetica, Arial, Geneva, sans-serif; -moz-border-radius: 6px 0px 0px 6px; -webkit-border-radius: 6px 0px 0px 6px; border-radius: 6px 0px 0px 6px; -moz-box-shadow: 0 0 20px rgba(0,0,0,0.5); -webkit-box-shadow: 0 0 20px rgba(0,0,0,0.5); box-shadow: 0 0 20px rgba(0,0,0,0.5); position:fixed; z-index:9999; bottom:0; right:0; font-size:15px; margin: 20px 0; display: block; background:#4E5969; } \
    #cp_popup.opened { width: 492px; } \
    #cp_popup a#add_to { cursor:pointer; text-align:center; text-decoration:none; color: #000; display:block; padding:5px 0 5px 5px; } \
    #cp_popup a#close_button { cursor:pointer; float: right; padding:120px 10px 10px; } \
    #cp_popup a img { vertical-align: middle; } \
    #cp_popup a:hover { color:#000; } \
    #cp_popup iframe{ background:#4E5969; margin:6px 0 2px 6px; height:140px; width:450px; overflow:hidden; border:none; } \
');

var cp_icon = 'data:image/png;base64,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';
var close_img = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAAABGdBTUEAALGOfPtRkwAAACBjSFJNAAB6JQAAgIMAAPn/AACA6QAAdTAAAOpgAAA6mAAAF2+SX8VGAAAA5ElEQVR42tRTQYoEIQwsl/2Bl3gQoY9eBKEf5kvyG8G7h4Z+S38gIu5lp5lZ2R7YPm1BDhZJSFWiGmPgDj5wE7cbfD4/mBkAHprUj9yTTyn9OsGIMSLG+Fxwxc8SiAi9d4QQHskjhIDeO4jorQcq5wwiQmsN3nt479FaAxEh5zxJmyZIKalSClprL1FKQUpJXZr4DBH52xqZeRhjICKw1sJaCxGBMQbMPN41GFpriAicc6i1otYK5xxEBFrraQuThGVZAADbtp2amXms6woAOI7j0gO17/t5MN+HNfEvBf//M30NAKe7aRqUOIlfAAAAAElFTkSuQmCC';

var osd = function(){
    var navbar, newElement;

    var createApiUrl = function(url){
        return host + api + "?url=" + escape(url)
    };

    var iframe = create('iframe', {
        'src': createApiUrl(document.location.href),
        'frameborder': 0,
        'scrolling': 'no'
    });

    var popup = create('div', {
        'id': 'cp_popup'
    });

    var onclick = function(){

        // Try and get imdb url
        try {
            var regex = new RegExp(/tt(\d{7})/);
            var imdb_id = document.body.innerHTML.match(regex)[0];
            if (imdb_id)
                iframe.setAttribute('src', createApiUrl('http://imdb.com/title/'+imdb_id+'/'))
        }
        catch(e){}

        popup.innerHTML = '';
        popup.setAttribute('class', 'opened');
        popup.appendChild(create('a', {
            'innerHTML': '<img src="' + close_img + '" />',
            'id': 'close_button',
            'onclick': function(){
                popup.innerHTML = '';
                popup.appendChild(add_button);
                popup.setAttribute('class', '');
            }
        }));
        popup.appendChild(iframe)
    }

    var add_button = create('a', {
        'innerHTML': '<img src="' + cp_icon + '" />',
        'id': 'add_to',
        'onclick': onclick
    });
    popup.appendChild(add_button);

    document.body.parentNode.insertBefore(popup, document.body);

    // Auto fold open
    if(document.body.getAttribute('cp_auto_open'))
    	onclick()
};

var setVersion = function(){
    document.body.setAttribute('data-userscript_version', version)
};

if(document.location.href.indexOf(host) == -1)
    osd();
else
    setVersion();

}