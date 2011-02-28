"""
Constant values about endian.
"""

from hachoir_core.i18n import _

BIG_ENDIAN = "ABCD"
LITTLE_ENDIAN = "DCBA"
NETWORK_ENDIAN = BIG_ENDIAN

endian_name = {
    BIG_ENDIAN: _("Big endian"),
    LITTLE_ENDIAN: _("Little endian"),
}

