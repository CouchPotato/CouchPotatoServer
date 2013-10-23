try:
    from collections import OrderedDict
except:
    from sleekxmpp.thirdparty.ordereddict import OrderedDict

try:
    from gnupg import GPG
except:
    from sleekxmpp.thirdparty.gnupg import GPG

from sleekxmpp.thirdparty.mini_dateutil import tzutc, tzoffset, parse_iso
