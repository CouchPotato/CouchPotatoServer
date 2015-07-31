/*
---
name: Form.CheckGroup
description: Class to represent a group of Form.Check wrapped checkboxes
authors: Bryan J Swift (@bryanjswift)
license: MIT-style license.
requires: [Core/Class.Extras, Core/Element, Core/Element.Event, Form-Replacement/Form.Check]
provides: Form.CheckGroup
...
*/
if (typeof window.Form === 'undefined') { window.Form = {}; }

Form.CheckGroup = new Class({
  Implements: [Events,Options],
  options: {
    checkOptions: {},
    initialValues: {}
  },
  checks: [],
  initialize: function(group,options) {
    if (!Form.Check) { throw 'required Class Form.Check not found'; }
    this.setOptions(options);
    group = $(group);
    if (!group) { return this; }
    var checkboxes = group.getElements('input[type=checkbox]');
    checkboxes.each(this.addCheck,this);
  },
  addCheck: function(checkbox) {
    var initialValues = this.options.initialValues[checkbox.get('name')];
    var checkOptions = {};
    checkOptions.checked = initialValues ? initialValues.contains(checkbox.get('value')) : checkbox.get('checked');
    checkOptions.disabled = checkbox.get('disabled');
    checkbox.store('Form.CheckGroup::data',this);
    var check = checkbox.retrieve('Form.Check::data') || new Form.Check(checkbox, Object.append(checkOptions,this.options.checkOptions));
    this.checks.push(check);
  },
  checkAll: function() {
    this.checks.each(function(check) { if (!check.checked) { check.toggle(); } });
  },
  disable: function() {
    this.checks.each(function(check) { check.disable(); });
    this.fireEvent('disable',this);
  },
  enable: function() {
    this.checks.each(function(check) { check.enable(); });
    this.fireEvent('enable',this);
  },
  uncheckAll: function() {
    this.checks.each(function(check) { if (check.checked) { check.toggle(); } });
  }
});
