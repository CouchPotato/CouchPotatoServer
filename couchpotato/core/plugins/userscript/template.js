// ==UserScript==
// @name        CouchPotato UserScript
// @description Add movies like a real CouchPotato

// @include     {{host}}*
{% for include in includes %}
// @include     {{include}}{% endfor %}
{% for exclude in excludes %}
// @exclude     {{exclude}}{% endfor %}
// ==/UserScript==

var version = {{version}},
    cpLocation = '{{host}}';

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
    #cpPopup { opacity: 0.5; width:200px; font-family: "Helvetica Neue", Helvetica, Arial, Geneva, sans-serif; -moz-border-radius-topleft: 6px; -moz-border-radius-topright: 6px; -webkit-border-top-left-radius: 6px; -webkit-border-top-right-radius: 6px; -moz-box-shadow: 0 0 20px rgba(0,0,0,0.5); -webkit-box-shadow: 0 0 20px rgba(0,0,0,0.5); position:fixed; z-index:9999; bottom:0; right:0; font-size:15px; margin: 0 20px; display: block; background:#f5f5f5; } \
    #cpPopup:hover { opacity: 1; } \
    #cpPopup a#addTo { cursor:pointer; text-align:center; text-decoration:none; color: #000; display:block; padding:15px 0 10px; } \
    #cpPopup a#closeBtn { cursor:pointer; float: right; padding:10px; } \
    #cpPopup a img { vertical-align: middle; } \
    #cpPopup a:hover { color:#000; } \
    #cpPopup iframe{ background:#f5f5f5; margin:6px; height:70px; width:188px; overflow:hidden; border:none; } \
');

var movieImg = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAZCAYAAABQDyyRAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAA+9JREFUeNrMVklIXFkUPVWWY5cDccIpMQ444YCi7UJ3KrpUxAkURRAFW6GdMCI0ooKuxIWCIkrc6FYMcYogrgxoEHFeRFRE42w5D/X73dv1i4pUOiGmkly4/u9779c979x7z3sKSZLwK02JX2y/BYCXwmeESybyGV0Mo6YQNTBzf38f09/fj7GxMRwcHPyQnTk5OSEpKQm5ublQqVTvxdCfXwIg9fT0YGBgAO7u7qipqUFAQACurq7Q29uLoaEhXhgdHY3q6mqo1WocHx+jpaUF8/PzPJeamor8/HwKhKWlJbS2tmJ/f5/nsrKyUFhYSK8vhG8+BmD2j7Dm5mZotVqcnp5ibW0N4eHhcHFxQUREBM7OznhsZ2cHu7u7iI2Nhb29PQOi8b29PaysrECpVCIqKgpubm4IDAzE7OwsLi8vsbW1hYyMDIrVK/yTUQDd3d2oqKjgjygFc3NzCAsLg7OzMyIjI3F+fo7V1VVsbm5ie3sbMTExsLW15acMYmFhAbe3twza1dUVwcHB0Gg0WF9fR15eHsXqNAZA3wUJCQkoKipiGilIQ0MDf2xmZsYUJicn87rp6Wmm+OLigpmglIWEhPDc4OAg+vr6cH19zSwUFBR8tVa4BhITE03aauPj4/QIE75gFMBPanmjAFT05ycxYNRU8svo6CiGh4fR2dkJoQvw8PBAXV0dfHx8cHNzw+MjIyO8Ni4uDpWVlbCxseGibWpqwuLiIs9lZ2cjJycHlpaW3DlTU1N6afhfABMTE+jq6uLgnp6eqK+v5+BU2aQTcvD4+HhUVVXB2toaJycnrAdy8MzMTNYDasnl5WUeIzA6eyWc0GiNdkFbWxvvlIKKzvxs57IYGQYnMWpsbNSLEQWibqHgBIiA2dnZIS0tDbW1taxlwm0o3YYp1zNwd3fHSlheXs4MUO+TElJaZCUsKyuDubk5q9xjJaTd02/ISkgAqR1JCw4PD+XNSiZvQysrKygUClhYWDCrpAX+/v7o6OjQiOkA4RpdGi4/Y+Cp5uDggJKSEj5HiAkCQSmU2T06OlILuadikURqbgXAt+K9khlIT0/nc+ApRqceSe63/FZQUBDa29vp9W9mICUlhU/DJ10slP/Vs6+vLx9gZNRRGxsb3JJeXl76td7e3vrPiIEPYmEEtdrk5CRR9V0AHB0dUVpaitDQUD0gOmGJEV0NUAEeGVxU3gn/CwLAS7qUSCYwUf2SOOSk4uJi+vdYuJtwtfA/6AQgpxR81N1WnIU//4EKbP7w8PBGPJ9REersTHTchaE8G3bBvs6fZHJLiwBW4vakJfr9/Py4JIx+IFNhAqf6em2QkT7hysfr/hVgAIhbr+v/xmSzAAAAAElFTkSuQmCC';
var closeImg = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAAABGdBTUEAALGOfPtRkwAAACBjSFJNAAB6JQAAgIMAAPn/AACA6QAAdTAAAOpgAAA6mAAAF2+SX8VGAAAA5ElEQVR42tRTQYoEIQwsl/2Bl3gQoY9eBKEf5kvyG8G7h4Z+S38gIu5lp5lZ2R7YPm1BDhZJSFWiGmPgDj5wE7cbfD4/mBkAHprUj9yTTyn9OsGIMSLG+Fxwxc8SiAi9d4QQHskjhIDeO4jorQcq5wwiQmsN3nt479FaAxEh5zxJmyZIKalSClprL1FKQUpJXZr4DBH52xqZeRhjICKw1sJaCxGBMQbMPN41GFpriAicc6i1otYK5xxEBFrraQuThGVZAADbtp2amXms6woAOI7j0gO17/t5MN+HNfEvBf//M30NAKe7aRqUOIlfAAAAAElFTkSuQmCC';

var osd = function(){
    var navbar, newElement;

    var iFrame = create('iframe', {
        'src': cpLocation + "userscript.add_via_url/?url=" + escape(document.location),
        'frameborder': 0,
        'scrolling': 'no'
    });

    var addToText = '<a class="addTo" href="#"></a>';
    var popupId = 'cpPopup';

    var popup = create('div', {
        'id': popupId,
        'innerHTML': addToText
    });
    var addButton = create('a', {
        'innerHTML': '<img src="' + movieImg + '" />Add to CouchPotato',
        'id': 'addTo',
        'onclick': function(){
            popup.innerHTML = '';
            popup.appendChild(create('a', {
                'innerHTML': '<img src="' + closeImg + '" />',
                'id': 'closeBtn',
                'onclick': function(){
                    popup.innerHTML = '';
                    popup.appendChild(addButton);
                }
            }));
            popup.appendChild(iFrame)
        }
    });
    popup.appendChild(addButton);

    document.body.parentNode.insertBefore(popup, document.body);
};

osd();