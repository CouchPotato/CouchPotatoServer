/*
---
name: Form.Check
description: Class to represent a checkbox
authors: Bryan J Swift (@bryanjswift)
license: MIT-style license.
requires: [Core/Class.Extras, Core/Element, Core/Element.Event]
provides: Form.Check
...
*/
if (typeof window.Form === 'undefined') { window.Form = {}; }

Form.Check = new Class({
  Implements: [Events, Options],
  options: {
    checked: false,
    disabled: false
  },
  bound: {},
  checked: false,
  config: {
    checkedClass: 'checked',
    disabledClass: 'disabled',
    elementClass: 'check',
    highlightedClass: 'highlighted',
    storage: 'Form.Check::data'
  },
  disabled: false,
  element: null,
  input: null,
  label: null,
  value: null,
  initialize: function(input, options) {
    this.setOptions(options);
    this.bound = {
      disable: this.disable.bind(this),
      enable: this.enable.bind(this),
      highlight: this.highlight.bind(this),
      removeHighlight: this.removeHighlight.bind(this),
      keyToggle: this.keyToggle.bind(this),
      toggle: this.toggle.bind(this)
    };
    var bound = this.bound;
    input = this.input = $(input);
    var id = input.get('id');
    this.label = document.getElement('label[for=' + id + ']');
    this.element = new Element('div', {
      'class': input.get('class') + ' ' + this.config.elementClass,
      id: id ? id + 'Check' : '',
      events: {
        click: bound.toggle,
        mouseenter: bound.highlight,
        mouseleave: bound.removeHighlight
      }
    });
    this.input.addEvents({
      keypress: bound.keyToggle,
      keydown: bound.keyToggle,
      keyup: bound.keyToggle
    });
    if (this.label) { this.label.addEvent('click', bound.toggle); }
    this.element.wraps(input);
    this.value = input.get('value');
    if (this.input.checked) { this.check(); } else { this.uncheck(); }
    if (this.input.disabled) { this.disable(); } else { this.enable(); }
    input.store(this.config.storage, this).addEvents({
      blur: bound.removeHighlight,
      focus: bound.highlight
    });
    this.fireEvent('create', this);
  },
  check: function() {
    this.element.addClass(this.config.checkedClass);
    this.input.set('checked', 'checked').focus();
    this.checked = true;
    this.fireEvent('check', this);
  },
  disable: function() {
    this.element.addClass(this.config.disabledClass);
    this.input.set('disabled', 'disabled');
    this.disabled = true;
    this.fireEvent('disable', this);
  },
  enable: function() {
    this.element.removeClass(this.config.disabledClass);
    this.input.erase('disabled');
    this.disabled = false;
    this.fireEvent('enable', this);
  },
  highlight: function() {
    this.element.addClass(this.config.highlightedClass);
    this.fireEvent('highlight', this);
  },
  removeHighlight: function() {
    this.element.removeClass(this.config.highlightedClass);
    this.fireEvent('removeHighlight', this);
  },
  keyToggle: function(e) {
    var evt = (e);
    if (evt.key === 'space') { this.toggle(e); }
  },
  toggle: function(e) {
    var evt;
    if (this.disabled) { return this; }
    if (e) {
      evt = (e).stopPropagation();
      if (evt.target.tagName.toLowerCase() !== 'a') {
        evt.stop();
      }
    }
    if (this.checked) {
      this.uncheck();
    } else {
      this.check();
    }
    this.fireEvent('change', this);
    this.input.fireEvent('change', this);
    return this;
  },
  uncheck: function() {
    this.element.removeClass(this.config.checkedClass);
    this.input.erase('checked');
    this.checked = false;
    this.fireEvent('uncheck', this);
  }
});
