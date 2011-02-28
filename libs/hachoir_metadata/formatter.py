from hachoir_core.i18n import _, ngettext

NB_CHANNEL_NAME = {1: _("mono"), 2: _("stereo")}

def humanAudioChannel(value):
    return NB_CHANNEL_NAME.get(value, unicode(value))

def humanFrameRate(value):
    if isinstance(value, (int, long, float)):
        return _("%.1f fps") % value
    else:
        return value

def humanComprRate(rate):
    return u"%.1fx" % rate

def humanAltitude(value):
    return ngettext("%.1f meter", "%.1f meters", value) % value

def humanPixelSize(value):
    return ngettext("%s pixel", "%s pixels", value) % value

def humanDPI(value):
    return u"%s DPI" % value

