"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class UserActivity(ElementBase):

    name = 'activity'
    namespace = 'http://jabber.org/protocol/activity'
    plugin_attrib = 'activity'
    interfaces = set(['value', 'text'])
    sub_interfaces = set(['text'])
    general = set(['doing_chores', 'drinking', 'eating', 'exercising',
                   'grooming', 'having_appointment', 'inactive', 'relaxing',
                   'talking', 'traveling', 'undefined', 'working'])
    specific = set(['at_the_spa', 'brushing_teeth', 'buying_groceries',
                    'cleaning', 'coding', 'commuting', 'cooking', 'cycling',
                    'dancing', 'day_off', 'doing_maintenance',
                    'doing_the_dishes', 'doing_the_laundry', 'driving',
                    'fishing', 'gaming', 'gardening', 'getting_a_haircut',
                    'going_out', 'hanging_out', 'having_a_beer',
                    'having_a_snack', 'having_breakfast', 'having_coffee',
                    'having_dinner', 'having_lunch', 'having_tea', 'hiding',
                    'hiking', 'in_a_car', 'in_a_meeting', 'in_real_life',
                    'jogging', 'on_a_bus', 'on_a_plane', 'on_a_train',
                    'on_a_trip', 'on_the_phone', 'on_vacation',
                    'on_video_phone', 'other', 'partying', 'playing_sports',
                    'praying', 'reading', 'rehearsing', 'running',
                    'running_an_errand', 'scheduled_holiday', 'shaving',
                    'shopping', 'skiing', 'sleeping', 'smoking',
                    'socializing', 'studying', 'sunbathing', 'swimming',
                    'taking_a_bath', 'taking_a_shower', 'thinking',
                    'walking', 'walking_the_dog', 'watching_a_movie',
                    'watching_tv', 'working_out', 'writing'])

    def set_value(self, value):
        self.del_value()
        general = value
        specific = None
        if isinstance(value, tuple) or isinstance(value, list):
            general = value[0]
            specific = value[1]

        if general in self.general:
            gen_xml = ET.Element('{%s}%s' % (self.namespace, general))
            if specific:
                spec_xml = ET.Element('{%s}%s' % (self.namespace, specific))
                if specific in self.specific:
                    gen_xml.append(spec_xml)
                else:
                    raise ValueError('Unknown specific activity')
            self.xml.append(gen_xml)
        else:
            raise ValueError('Unknown general activity')

    def get_value(self):
        general = None
        specific = None
        gen_xml = None
        for child in self.xml:
            if child.tag.startswith('{%s}' % self.namespace):
                elem_name = child.tag.split('}')[-1]
                if elem_name in self.general:
                    general = elem_name
                    gen_xml = child
        if gen_xml is not None:
            for child in gen_xml:
                if child.tag.startswith('{%s}' % self.namespace):
                    elem_name = child.tag.split('}')[-1]
                    if elem_name in self.specific:
                        specific = elem_name
        return (general, specific)

    def del_value(self):
        curr_value = self.get_value()
        if curr_value[0]:
            self._set_sub_text(curr_value[0], '', keep=False)
