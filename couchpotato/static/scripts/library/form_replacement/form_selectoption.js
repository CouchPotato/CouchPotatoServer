/*
---
name: Form.SelectOption
description: Class to represent an option for Form.Dropdown
authors: Bryan J Swift (@bryanjswift)
license: MIT-style license.
requires: [Core/Class.Extras, Core/Element, Core/Element.Event]
provides: Form.SelectOption
...
*/
if (typeof window.Form === 'undefined') { window.Form = {}; }

Form.SelectOption = new Class({
  Implements: [Events, Options],
  options: {
    optionTag: 'li',
    selected: false
  },
  config: {
    highlightedClass: 'highlighted',
    optionClass: 'option',
    selectedClass: 'selected'
  },
  element: null,
  bound: {},
  option: null,
  selected: false,
  text: null,
  value: null,
  initialize: function(option, options) {
    this.setOptions(options);
    option = $(option);
    this.option = option;
    this.bound = {
      deselect: this.deselect.bind(this),
      highlight: this.highlight.bind(this),
      removeHighlight: this.removeHighlight.bind(this),
      select: this.select.bind(this)
    };
    this.text = option.get('text');
    this.value = option.get('value');
    this.element = new Element(this.options.optionTag, {
      'class': (option.get('class') + ' ' + this.config.optionClass).trim(),
      'html': option.get('html'),
      'events': {
        click: this.bound.select,
        mouseenter: this.bound.highlight,
        mouseleave: this.bound.removeHighlight
      }
    });
    this.element.store('Form.SelectOption::data', this);
    option.store('Form.SelectOption::data', this);
  },
  deselect: function(e) {
    this.fireEvent('onDeselect', [this, e]);
    this.element.removeClass(this.config.selectedClass).addEvent('click', this.bound.select);
    this.selected = false;
  },
  destroy: function() {
    this.element = null;
    this.bound = null;
    this.option = null;
  },
  disable: function() {
    this.element.removeEvents({
      mouseenter: this.bound.highlight,
      mouseleave: this.bound.removeHighlight
    });
    this.fireEvent('onDisable', this);
  },
  enable: function() {
    this.element.addEvents({
      mouseenter: this.bound.highlight,
      mouseleave: this.bound.removeHighlight
    });
    this.fireEvent('onEnable', this);
  },
  highlight: function(e) {
    this.fireEvent('onHighlight', [this, e]);
    this.element.addClass(this.config.highlightedClass);
    return this;
  },
  removeHighlight: function(e) {
    this.fireEvent('onRemoveHighlight', [this, e]);
    this.element.removeClass(this.config.highlightedClass);
    return this;
  },
  select: function(e) {
    this.fireEvent('onSelect', [this, e]);
    this.element.addClass(this.config.selectedClass).removeEvent('click', this.bound.select);
    this.selected = true;
  }
});
