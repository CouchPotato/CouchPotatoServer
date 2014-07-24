from couchpotato.core.media import MediaBase


class ShowTypeBase(MediaBase):
    _type = 'show'

    def getType(self):
        if hasattr(self, 'type') and self.type != self._type:
            return '%s.%s' % (self._type, self.type)

        return self._type
