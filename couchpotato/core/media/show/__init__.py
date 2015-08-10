from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.media import MediaBase

autoload = 'ShowToggler'


class ShowToggler(MediaBase):
    """
    TV Show support is EXPERIMENTAL and disabled by default. The "Shows" item
    must only be visible if the user enabled it. This class notifies the
    frontend if the shows.enabled configuration item changed.

    FIXME: remove after TV Show support is considered stable.
    """
    def __init__(self):
        addEvent('setting.save.shows.enabled.after', self.toggleTab)

    def toggleTab(self):
        fireEvent('notify.frontend', type = 'shows.enabled', data = self.conf('enabled', section='shows'))


class ShowTypeBase(MediaBase):
    _type = 'show'

    def getType(self):
        if hasattr(self, 'type') and self.type != self._type:
            return '%s.%s' % (self._type, self.type)

        return self._type

config = [{
    'name': 'shows',
    'groups': [
        {
            'tab': 'general',
            'name': 'Shows',
            'label': 'Shows',
            'description': 'Enable EXPERIMENTAL TV Show support',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'prefer_episode_releases',
                    'default': False,
                    'type': 'bool',
                    'label': 'Episode releases',
                    'description': 'Prefer episode releases over season packs',
                },
            ],
        },
    ],
}]