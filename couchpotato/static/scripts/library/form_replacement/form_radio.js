/*
---
name: Form.Radio
description: Class to represent a radio button
authors: Bryan J Swift (@bryanjswift)
license: MIT-style license.
requires: [Core/Class.Extras, Core/Element, Core/Element.Event, Form-Replacement/Form.Check]
provides: Form.Radio
...
*/
if (typeof window.Form === 'undefined') { window.Form = {}; }

Form.Radio = new Class({
  Extends: Form.Check,
  config: {
    elementClass: 'radio',
    storage: 'Form.Radio::data'
  },
  initialize: function(input,options) {
    this.parent(input,options);
  },
  toggle: function(e) {
    if (this.element.hasClass('checked') || this.disabled) { return; }
    var evt;
    if (e) { evt = (e).stop(); }
    if (this.checked) {
      this.uncheck();
    } else {
      this.check();
    }
    this.fireEvent(this.checked ? 'onCheck' : 'onUncheck',this);
    this.fireEvent('onChange',this);
  }
});