"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class DiscoInfo(ElementBase):

    """
    XMPP allows for users and agents to find the identities and features
    supported by other entities in the XMPP network through service discovery,
    or "disco". In particular, the "disco#info" query type for <iq> stanzas is
    used to request the list of identities and features offered by a JID.

    An identity is a combination of a category and type, such as the 'client'
    category with a type of 'pc' to indicate the agent is a human operated
    client with a GUI, or a category of 'gateway' with a type of 'aim' to
    identify the agent as a gateway for the legacy AIM protocol. See
    <http://xmpp.org/registrar/disco-categories.html> for a full list of
    accepted category and type combinations.

    Features are simply a set of the namespaces that identify the supported
    features. For example, a client that supports service discovery will
    include the feature 'http://jabber.org/protocol/disco#info'.

    Since clients and components may operate in several roles at once, identity
    and feature information may be grouped into "nodes". If one were to write
    all of the identities and features used by a client, then node names would
    be like section headings.

    Example disco#info stanzas:
        <iq type="get">
          <query xmlns="http://jabber.org/protocol/disco#info" />
        </iq>

        <iq type="result">
          <query xmlns="http://jabber.org/protocol/disco#info">
            <identity category="client" type="bot" name="SleekXMPP Bot" />
            <feature var="http://jabber.org/protocol/disco#info" />
            <feature var="jabber:x:data" />
            <feature var="urn:xmpp:ping" />
          </query>
        </iq>

    Stanza Interface:
        node       -- The name of the node to either
                      query or return info from.
        identities -- A set of 4-tuples, where each tuple contains
                      the category, type, xml:lang, and name
                      of an identity.
        features   -- A set of namespaces for features.

    Methods:
        add_identity   -- Add a new, single identity.
        del_identity   -- Remove a single identity.
        get_identities -- Return all identities in tuple form.
        set_identities -- Use multiple identities, each given in tuple form.
        del_identities -- Remove all identities.
        add_feature    -- Add a single feature.
        del_feature    -- Remove a single feature.
        get_features   -- Return a list of all features.
        set_features   -- Use a given list of features.
        del_features   -- Remove all features.
    """

    name = 'query'
    namespace = 'http://jabber.org/protocol/disco#info'
    plugin_attrib = 'disco_info'
    interfaces = set(('node', 'features', 'identities'))
    lang_interfaces = set(('identities',))

    # Cache identities and features
    _identities = set()
    _features = set()

    def setup(self, xml=None):
        """
        Populate the stanza object using an optional XML object.

        Overrides ElementBase.setup

        Caches identity and feature information.

        Arguments:
            xml -- Use an existing XML object for the stanza's values.
        """
        ElementBase.setup(self, xml)

        self._identities = set([id[0:3] for id in self['identities']])
        self._features = self['features']

    def add_identity(self, category, itype, name=None, lang=None):
        """
        Add a new identity element. Each identity must be unique
        in terms of all four identity components.

        Multiple, identical category/type pairs are allowed only
        if the xml:lang values are different. Likewise, multiple
        category/type/xml:lang pairs are allowed so long as the names
        are different. In any case, a category and type are required.

        Arguments:
            category -- The general category to which the agent belongs.
            itype    -- A more specific designation with the category.
            name     -- Optional human readable name for this identity.
            lang     -- Optional standard xml:lang value.
        """
        identity = (category, itype, lang)
        if identity not in self._identities:
            self._identities.add(identity)
            id_xml = ET.Element('{%s}identity' % self.namespace)
            id_xml.attrib['category'] = category
            id_xml.attrib['type'] = itype
            if lang:
                id_xml.attrib['{%s}lang' % self.xml_ns] = lang
            if name:
                id_xml.attrib['name'] = name
            self.xml.append(id_xml)
            return True
        return False

    def del_identity(self, category, itype, name=None, lang=None):
        """
        Remove a given identity.

        Arguments:
            category -- The general category to which the agent belonged.
            itype    -- A more specific designation with the category.
            name     -- Optional human readable name for this identity.
            lang     -- Optional, standard xml:lang value.
        """
        identity = (category, itype, lang)
        if identity in self._identities:
            self._identities.remove(identity)
            for id_xml in self.findall('{%s}identity' % self.namespace):
                id = (id_xml.attrib['category'],
                      id_xml.attrib['type'],
                      id_xml.attrib.get('{%s}lang' % self.xml_ns, None))
                if id == identity:
                    self.xml.remove(id_xml)
                    return True
        return False

    def get_identities(self, lang=None, dedupe=True):
        """
        Return a set of all identities in tuple form as so:
            (category, type, lang, name)

        If a language was specified, only return identities using
        that language.

        Arguments:
            lang   -- Optional, standard xml:lang value.
            dedupe -- If True, de-duplicate identities, otherwise
                      return a list of all identities.
        """
        if dedupe:
            identities = set()
        else:
            identities = []
        for id_xml in self.findall('{%s}identity' % self.namespace):
            xml_lang = id_xml.attrib.get('{%s}lang' % self.xml_ns, None)
            if lang is None or xml_lang == lang:
                id = (id_xml.attrib['category'],
                      id_xml.attrib['type'],
                      id_xml.attrib.get('{%s}lang' % self.xml_ns, None),
                      id_xml.attrib.get('name', None))
                if dedupe:
                    identities.add(id)
                else:
                    identities.append(id)
        return identities

    def set_identities(self, identities, lang=None):
        """
        Add or replace all identities. The identities must be a in set
        where each identity is a tuple of the form:
            (category, type, lang, name)

        If a language is specifified, any identities using that language
        will be removed to be replaced with the given identities.

        NOTE: An identity's language will not be changed regardless of
              the value of lang.

        Arguments:
            identities -- A set of identities in tuple form.
            lang       -- Optional, standard xml:lang value.
        """
        self.del_identities(lang)
        for identity in identities:
            category, itype, lang, name = identity
            self.add_identity(category, itype, name, lang)

    def del_identities(self, lang=None):
        """
        Remove all identities. If a language was specified, only
        remove identities using that language.

        Arguments:
            lang -- Optional, standard xml:lang value.
        """
        for id_xml in self.findall('{%s}identity' % self.namespace):
            if lang is None:
                self.xml.remove(id_xml)
            elif id_xml.attrib.get('{%s}lang' % self.xml_ns, None) == lang:
                self._identities.remove((
                    id_xml.attrib['category'],
                    id_xml.attrib['type'],
                    id_xml.attrib.get('{%s}lang' % self.xml_ns, None)))
                self.xml.remove(id_xml)

    def add_feature(self, feature):
        """
        Add a single, new feature.

        Arguments:
            feature -- The namespace of the supported feature.
        """
        if feature not in self._features:
            self._features.add(feature)
            feature_xml = ET.Element('{%s}feature' % self.namespace)
            feature_xml.attrib['var'] = feature
            self.xml.append(feature_xml)
            return True
        return False

    def del_feature(self, feature):
        """
        Remove a single feature.

        Arguments:
            feature -- The namespace of the removed feature.
        """
        if feature in self._features:
            self._features.remove(feature)
            for feature_xml in self.findall('{%s}feature' % self.namespace):
                if feature_xml.attrib['var'] == feature:
                    self.xml.remove(feature_xml)
                    return True
        return False

    def get_features(self, dedupe=True):
        """Return the set of all supported features."""
        if dedupe:
            features = set()
        else:
            features = []
        for feature_xml in self.findall('{%s}feature' % self.namespace):
            if dedupe:
                features.add(feature_xml.attrib['var'])
            else:
                features.append(feature_xml.attrib['var'])
        return features

    def set_features(self, features):
        """
        Add or replace the set of supported features.

        Arguments:
            features -- The new set of supported features.
        """
        self.del_features()
        for feature in features:
            self.add_feature(feature)

    def del_features(self):
        """Remove all features."""
        self._features = set()
        for feature_xml in self.findall('{%s}feature' % self.namespace):
            self.xml.remove(feature_xml)
