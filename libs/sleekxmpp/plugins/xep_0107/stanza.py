"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class UserMood(ElementBase):

    name = 'mood'
    namespace = 'http://jabber.org/protocol/mood'
    plugin_attrib = 'mood'
    interfaces = set(['value', 'text'])
    sub_interfaces = set(['text'])
    moods = set(['afraid', 'amazed', 'amorous', 'angry', 'annoyed', 'anxious',
                 'aroused', 'ashamed', 'bored', 'brave', 'calm', 'cautious',
                 'cold', 'confident', 'confused', 'contemplative', 'contented',
                 'cranky', 'crazy', 'creative', 'curious', 'dejected',
                 'depressed', 'disappointed', 'disgusted', 'dismayed',
                 'distracted', 'embarrassed', 'envious', 'excited',
                 'flirtatious', 'frustrated', 'grateful', 'grieving', 'grumpy',
                 'guilty', 'happy', 'hopeful', 'hot', 'humbled', 'humiliated',
                 'hungry', 'hurt', 'impressed', 'in_awe', 'in_love',
                 'indignant', 'interested', 'intoxicated', 'invincible',
                 'jealous', 'lonely', 'lost', 'lucky', 'mean', 'moody',
                 'nervous', 'neutral', 'offended', 'outraged', 'playful',
                 'proud', 'relaxed', 'relieved', 'remorseful', 'restless',
                 'sad', 'sarcastic', 'satisfied', 'serious', 'shocked',
                 'shy', 'sick', 'sleepy', 'spontaneous', 'stressed', 'strong',
                 'surprised', 'thankful', 'thirsty', 'tired', 'undefined',
                 'weak', 'worried'])

    def set_value(self, value):
        self.del_value()
        if value in self.moods:
            self._set_sub_text(value, '', keep=True)
        else:
            raise ValueError('Unknown mood value')

    def get_value(self):
        for child in self.xml:
            if child.tag.startswith('{%s}' % self.namespace):
                elem_name = child.tag.split('}')[-1]
                if elem_name in self.moods:
                    return elem_name
        return ''

    def del_value(self):
        curr_value = self.get_value()
        if curr_value:
            self._set_sub_text(curr_value, '', keep=False)
