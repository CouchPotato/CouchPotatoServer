"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from xml.parsers.expat import ExpatError

from sleekxmpp.xmlstream.stanzabase import ET
from sleekxmpp.xmlstream.matcher.base import MatcherBase


# Flag indicating if the builtin XPath matcher should be used, which
# uses namespaces, or a custom matcher that ignores namespaces.
# Changing this will affect ALL XMLMask matchers.
IGNORE_NS = False


log = logging.getLogger(__name__)


class MatchXMLMask(MatcherBase):

    """
    The XMLMask matcher selects stanzas whose XML matches a given
    XML pattern, or mask. For example, message stanzas with body elements
    could be matched using the mask:

    .. code-block:: xml

        <message xmlns="jabber:client"><body /></message>

    Use of XMLMask is discouraged, and
    :class:`~sleekxmpp.xmlstream.matcher.xpath.MatchXPath` or
    :class:`~sleekxmpp.xmlstream.matcher.stanzapath.StanzaPath`
    should be used instead.

    The use of namespaces in the mask comparison is controlled by
    ``IGNORE_NS``. Setting ``IGNORE_NS`` to ``True`` will disable namespace
    based matching for ALL XMLMask matchers.

    :param criteria: Either an :class:`~xml.etree.ElementTree.Element` XML
                     object or XML string to use as a mask.
    """

    def __init__(self, criteria):
        MatcherBase.__init__(self, criteria)
        if isinstance(criteria, str):
            self._criteria = ET.fromstring(self._criteria)
        self.default_ns = 'jabber:client'

    def setDefaultNS(self, ns):
        """Set the default namespace to use during comparisons.

        :param ns: The new namespace to use as the default.
        """
        self.default_ns = ns

    def match(self, xml):
        """Compare a stanza object or XML object against the stored XML mask.

        Overrides MatcherBase.match.

        :param xml: The stanza object or XML object to compare against.
        """
        if hasattr(xml, 'xml'):
            xml = xml.xml
        return self._mask_cmp(xml, self._criteria, True)

    def _mask_cmp(self, source, mask, use_ns=False, default_ns='__no_ns__'):
        """Compare an XML object against an XML mask.

        :param source: The :class:`~xml.etree.ElementTree.Element` XML object
                       to compare against the mask.
        :param mask: The :class:`~xml.etree.ElementTree.Element` XML object
                     serving as the mask.
        :param use_ns: Indicates if namespaces should be respected during
                       the comparison.
        :default_ns: The default namespace to apply to elements that
                     do not have a specified namespace.
                     Defaults to ``"__no_ns__"``.
        """
        use_ns = not IGNORE_NS

        if source is None:
            # If the element was not found. May happend during recursive calls.
            return False

        # Convert the mask to an XML object if it is a string.
        if not hasattr(mask, 'attrib'):
            try:
                mask = ET.fromstring(mask)
            except ExpatError:
                log.warning("Expat error: %s\nIn parsing: %s", '', mask)
        if not use_ns:
            # Compare the element without using namespaces.
            source_tag = source.tag.split('}', 1)[-1]
            mask_tag = mask.tag.split('}', 1)[-1]
            if source_tag != mask_tag:
                return False
        else:
            # Compare the element using namespaces
            mask_ns_tag = "{%s}%s" % (self.default_ns, mask.tag)
            if source.tag not in [mask.tag, mask_ns_tag]:
                return False

        # If the mask includes text, compare it.
        if mask.text and source.text and \
           source.text.strip() != mask.text.strip():
            return False

        # Compare attributes. The stanza must include the attributes
        # defined by the mask, but may include others.
        for name, value in mask.attrib.items():
            if source.attrib.get(name, "__None__") != value:
                return False

        # Recursively check subelements.
        matched_elements = {}
        for subelement in mask:
            if use_ns:
                matched = False
                for other in source.findall(subelement.tag):
                    matched_elements[other] = False
                    if self._mask_cmp(other, subelement, use_ns):
                        if not matched_elements.get(other, False):
                            matched_elements[other] = True
                            matched = True
                if not matched:
                    return False
            else:
                if not self._mask_cmp(self._get_child(source, subelement.tag),
                                      subelement, use_ns):
                    return False

        # Everything matches.
        return True

    def _get_child(self, xml, tag):
        """Return a child element given its tag, ignoring namespace values.

        Returns ``None`` if the child was not found.

        :param xml: The :class:`~xml.etree.ElementTree.Element` XML object
                    to search for the given child tag.
        :param tag: The name of the subelement to find.
        """
        tag = tag.split('}')[-1]
        try:
            children = [c.tag.split('}')[-1] for c in xml]
            index = children.index(tag)
        except ValueError:
            return None
        return list(xml)[index]
