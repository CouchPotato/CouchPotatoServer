# BER decoder
from pyasn1.type import tag, base, univ, char, useful, tagmap
from pyasn1.codec.ber import eoo
from pyasn1.compat.octets import oct2int, octs2ints
from pyasn1 import error

class AbstractDecoder:
    protoComponent = None
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        raise error.PyAsn1Error('Decoder not implemented for %s' % tagSet)

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        raise error.PyAsn1Error('Indefinite length mode decoder not implemented for %s' % tagSet)

class AbstractSimpleDecoder(AbstractDecoder):
    def _createComponent(self, asn1Spec, tagSet, value=None):
        if asn1Spec is None:
            return self.protoComponent.clone(value, tagSet)
        elif value is None:
            return asn1Spec
        else:
            return asn1Spec.clone(value)
        
class AbstractConstructedDecoder(AbstractDecoder):
    def _createComponent(self, asn1Spec, tagSet, value=None):
        if asn1Spec is None:
            return self.protoComponent.clone(tagSet)
        else:
            return asn1Spec.clone()
                                
class EndOfOctetsDecoder(AbstractSimpleDecoder):
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        return eoo.endOfOctets, substrate[:length]

class ExplicitTagDecoder(AbstractSimpleDecoder):
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        return decodeFun(substrate[:length], asn1Spec, tagSet, length)

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun):
        value, substrate = decodeFun(substrate, asn1Spec, tagSet, length)
        terminator, substrate = decodeFun(substrate)
        if terminator == eoo.endOfOctets:
            return value, substrate
        else:
            raise error.PyAsn1Error('Missing end-of-octets terminator')

explicitTagDecoder = ExplicitTagDecoder()

class IntegerDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Integer(0)
    precomputedValues = {
        '\x00':  0,
        '\x01':  1,
        '\x02':  2,
        '\x03':  3,
        '\x04':  4,
        '\x05':  5,
        '\x06':  6,
        '\x07':  7,
        '\x08':  8,
        '\x09':  9,
        '\xff': -1,
        '\xfe': -2,
        '\xfd': -3,
        '\xfc': -4,
        '\xfb': -5
        }
    
    def _valueFilter(self, value):
        try:
            return int(value)
        except OverflowError:
            return value
        
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun):
        substrate = substrate[:length]
        if not substrate:
            raise error.PyAsn1Error('Empty substrate')
        if substrate in self.precomputedValues:
            value = self.precomputedValues[substrate]
        else:
            firstOctet = oct2int(substrate[0])
            if firstOctet & 0x80:
                value = -1
            else:
                value = 0
            for octet in substrate:
                value = value << 8 | oct2int(octet)
            value = self._valueFilter(value)
        return self._createComponent(asn1Spec, tagSet, value), substrate

class BooleanDecoder(IntegerDecoder):
    protoComponent = univ.Boolean(0)
    def _valueFilter(self, value):
        if value:
            return 1
        else:
            return 0

class BitStringDecoder(AbstractSimpleDecoder):
    protoComponent = univ.BitString(())
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun):
        substrate = substrate[:length]        
        if tagSet[0][1] == tag.tagFormatSimple:    # XXX what tag to check?
            if not substrate:
                raise error.PyAsn1Error('Missing initial octet')
            trailingBits = oct2int(substrate[0])
            if trailingBits > 7:
                raise error.PyAsn1Error(
                    'Trailing bits overflow %s' % trailingBits
                    )
            substrate = substrate[1:]
            lsb = p = 0; l = len(substrate)-1; b = ()
            while p <= l:
                if p == l:
                    lsb = trailingBits
                j = 7                    
                o = oct2int(substrate[p])
                while j >= lsb:
                    b = b + ((o>>j)&0x01,)
                    j = j - 1
                p = p + 1
            return self._createComponent(asn1Spec, tagSet, b), ''
        r = self._createComponent(asn1Spec, tagSet, ())
        if not decodeFun:
            return r, substrate
        while substrate:
            component, substrate = decodeFun(substrate)
            r = r + component
        return r, substrate

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun):
        r = self._createComponent(asn1Spec, tagSet, '')
        if not decodeFun:
            return r, substrate
        while substrate:
            component, substrate = decodeFun(substrate)
            if component == eoo.endOfOctets:
                break
            r = r + component
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        return r, substrate

class OctetStringDecoder(AbstractSimpleDecoder):
    protoComponent = univ.OctetString('')
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun):
        substrate = substrate[:length]
        if tagSet[0][1] == tag.tagFormatSimple:    # XXX what tag to check?
            return self._createComponent(asn1Spec, tagSet, substrate), ''
        r = self._createComponent(asn1Spec, tagSet, '')
        if not decodeFun:
            return r, substrate
        while substrate:
            component, substrate = decodeFun(substrate)
            r = r + component
        return r, substrate

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun):
        r = self._createComponent(asn1Spec, tagSet, '')
        if not decodeFun:
            return r, substrate        
        while substrate:
            component, substrate = decodeFun(substrate)
            if component == eoo.endOfOctets:
                break
            r = r + component
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        return r, substrate

class NullDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Null('')
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        substrate = substrate[:length]        
        r = self._createComponent(asn1Spec, tagSet)
        if substrate:
            raise error.PyAsn1Error('Unexpected substrate for Null')
        return r, substrate

class ObjectIdentifierDecoder(AbstractSimpleDecoder):
    protoComponent = univ.ObjectIdentifier(())
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun):
        substrate = substrate[:length]        
        if not substrate:
            raise error.PyAsn1Error('Empty substrate')
        oid = (); index = 0        
        # Get the first subid
        subId = oct2int(substrate[index])
        oid = oid + divmod(subId, 40)

        index = index + 1
        substrateLen = len(substrate)
        
        while index < substrateLen:
            subId = oct2int(substrate[index])
            if subId < 128:
                oid = oid + (subId,)
                index = index + 1
            else:
                # Construct subid from a number of octets
                nextSubId = subId
                subId = 0
                while nextSubId >= 128 and index < substrateLen:
                    subId = (subId << 7) + (nextSubId & 0x7F)
                    index = index + 1
                    nextSubId = oct2int(substrate[index])
                if index == substrateLen:
                    raise error.SubstrateUnderrunError(
                        'Short substrate for OID %s' % oid
                        )
                subId = (subId << 7) + nextSubId
                oid = oid + (subId,)
                index = index + 1
        return self._createComponent(asn1Spec, tagSet, oid), substrate[index:]

class RealDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Real()
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        substrate = substrate[:length]
        if not length:
            raise error.SubstrateUnderrunError('Short substrate for Real')
        fo = oct2int(substrate[0]); substrate = substrate[1:]
        if fo & 0x40:  # infinite value
            value = fo & 0x01 and '-inf' or 'inf'
        elif fo & 0x80:  # binary enoding
            if fo & 0x11 == 0:
                n = 1
            elif fo & 0x01:
                n = 2
            elif fo & 0x02:
                n = 3
            else:
                n = oct2int(substrate[0])
            eo, substrate = substrate[:n], substrate[n:]
            if not eo or not substrate:
                raise error.PyAsn1Error('Real exponent screwed')
            e = 0
            while eo:         # exponent
                e <<= 8
                e |= oct2int(eo[0])
                eo = eo[1:]
            p = 0
            while substrate:  # value
                p <<= 8
                p |= oct2int(substrate[0])
                substrate = substrate[1:]
            if fo & 0x40:    # sign bit
                p = -p
            value = (p, 2, e)
        elif fo & 0xc0 == 0:  # character encoding
            try:
                if fo & 0x3 == 0x1:  # NR1
                    value = (int(substrate), 10, 0)
                elif fo & 0x3 == 0x2:  # NR2
                    value = float(substrate)
                elif fo & 0x3 == 0x3:  # NR3
                    value = float(substrate)
                else:
                    raise error.SubstrateUnderrunError(
                        'Unknown NR (tag %s)' % fo
                        )
            except ValueError:
                raise error.SubstrateUnderrunError(
                    'Bad character Real syntax'
                    )
        elif fo & 0xc0 == 0x40:  # special real value
            pass
        else:
            raise error.SubstrateUnderrunError(
                'Unknown encoding (tag %s)' % fo
                )
        return self._createComponent(asn1Spec, tagSet, value), substrate
        
class SequenceDecoder(AbstractConstructedDecoder):
    protoComponent = univ.Sequence()
    def _getComponentTagMap(self, r, idx):
        try:
            return r.getComponentTagMapNearPosition(idx)
        except error.PyAsn1Error:
            return

    def _getComponentPositionByType(self, r, t, idx):
        return r.getComponentPositionNearType(t, idx)
    
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        substrate = substrate[:length]
        r = self._createComponent(asn1Spec, tagSet)
        idx = 0
        if not decodeFun:
            return r, substrate
        while substrate:
            asn1Spec = self._getComponentTagMap(r, idx)
            component, substrate = decodeFun(
                substrate, asn1Spec
                )
            idx = self._getComponentPositionByType(
                r, component.getEffectiveTagSet(), idx
                )
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1
        r.setDefaultComponents()
        r.verifySizeSpec()
        return r, substrate

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun):
        r = self._createComponent(asn1Spec, tagSet)
        idx = 0
        while substrate:
            asn1Spec = self._getComponentTagMap(r, idx)
            if not decodeFun:
                return r, substrate
            component, substrate = decodeFun(substrate, asn1Spec)
            if component == eoo.endOfOctets:
                break
            idx = self._getComponentPositionByType(
                r, component.getEffectiveTagSet(), idx
                )            
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1                
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        r.setDefaultComponents()
        r.verifySizeSpec()
        return r, substrate

class SequenceOfDecoder(AbstractConstructedDecoder):
    protoComponent = univ.SequenceOf()    
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        substrate = substrate[:length]
        r = self._createComponent(asn1Spec, tagSet)
        asn1Spec = r.getComponentType()
        idx = 0
        if not decodeFun:
            return r, substrate
        while substrate:
            component, substrate = decodeFun(
                substrate, asn1Spec
                )
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1
        r.verifySizeSpec()
        return r, substrate

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun):
        r = self._createComponent(asn1Spec, tagSet)
        asn1Spec = r.getComponentType()
        idx = 0
        if not decodeFun:
            return r, substrate
        while substrate:
            component, substrate = decodeFun(substrate, asn1Spec)
            if component == eoo.endOfOctets:
                break
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1                
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        r.verifySizeSpec()
        return r, substrate

class SetDecoder(SequenceDecoder):
    protoComponent = univ.Set()
    def _getComponentTagMap(self, r, idx):
        return r.getComponentTagMap()

    def _getComponentPositionByType(self, r, t, idx):
        nextIdx = r.getComponentPositionByType(t)
        if nextIdx is None:
            return idx
        else:
            return nextIdx
    
class SetOfDecoder(SequenceOfDecoder):
    protoComponent = univ.SetOf()
    
class ChoiceDecoder(AbstractConstructedDecoder):
    protoComponent = univ.Choice()
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        substrate = substrate[:length]        
        r = self._createComponent(asn1Spec, tagSet)
        if not decodeFun:
            return r, substrate
        if r.getTagSet() == tagSet: # explicitly tagged Choice
            component, substrate = decodeFun(
                substrate, r.getComponentTagMap()
                )
        else:
            component, substrate = decodeFun(
                substrate, r.getComponentTagMap(), tagSet, length, state
                )
        if isinstance(component, univ.Choice):
            effectiveTagSet = component.getEffectiveTagSet()
        else:
            effectiveTagSet = component.getTagSet()
        r.setComponentByType(effectiveTagSet, component, 0, asn1Spec is None)
        return r, substrate

    indefLenValueDecoder = valueDecoder

class AnyDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Any()
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun):
        if asn1Spec is None or \
               asn1Spec is not None and tagSet != asn1Spec.getTagSet():
            # untagged Any container, recover inner header substrate
            length = length + len(fullSubstrate) - len(substrate)
            substrate = fullSubstrate
        substrate = substrate[:length]
        return self._createComponent(asn1Spec, tagSet, value=substrate), ''

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun):
        if asn1Spec is not None and tagSet == asn1Spec.getTagSet():
            # tagged Any type -- consume header substrate
            header = ''
        else:
            # untagged Any, recover header substrate
            header = fullSubstrate[:-len(substrate)]

        r = self._createComponent(asn1Spec, tagSet, header)

        # Any components do not inherit initial tag
        asn1Spec = self.protoComponent
        
        if not decodeFun:
            return r, substrate
        while substrate:
            component, substrate = decodeFun(substrate, asn1Spec)
            if component == eoo.endOfOctets:
                break
            r = r + component
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        return r, substrate

# character string types
class UTF8StringDecoder(OctetStringDecoder):
    protoComponent = char.UTF8String()
class NumericStringDecoder(OctetStringDecoder):
    protoComponent = char.NumericString()
class PrintableStringDecoder(OctetStringDecoder):
    protoComponent = char.PrintableString()
class TeletexStringDecoder(OctetStringDecoder):
    protoComponent = char.TeletexString()
class VideotexStringDecoder(OctetStringDecoder):
    protoComponent = char.VideotexString()
class IA5StringDecoder(OctetStringDecoder):
    protoComponent = char.IA5String()
class GraphicStringDecoder(OctetStringDecoder):
    protoComponent = char.GraphicString()
class VisibleStringDecoder(OctetStringDecoder):
    protoComponent = char.VisibleString()
class GeneralStringDecoder(OctetStringDecoder):
    protoComponent = char.GeneralString()
class UniversalStringDecoder(OctetStringDecoder):
    protoComponent = char.UniversalString()
class BMPStringDecoder(OctetStringDecoder):
    protoComponent = char.BMPString()

# "useful" types
class GeneralizedTimeDecoder(OctetStringDecoder):
    protoComponent = useful.GeneralizedTime()
class UTCTimeDecoder(OctetStringDecoder):
    protoComponent = useful.UTCTime()

tagMap = {
    eoo.endOfOctets.tagSet: EndOfOctetsDecoder(),
    univ.Integer.tagSet: IntegerDecoder(),
    univ.Boolean.tagSet: BooleanDecoder(),
    univ.BitString.tagSet: BitStringDecoder(),
    univ.OctetString.tagSet: OctetStringDecoder(),
    univ.Null.tagSet: NullDecoder(),
    univ.ObjectIdentifier.tagSet: ObjectIdentifierDecoder(),
    univ.Enumerated.tagSet: IntegerDecoder(),
    univ.Real.tagSet: RealDecoder(),
    univ.Sequence.tagSet: SequenceDecoder(),  # conflicts with SequenceOf
    univ.Set.tagSet: SetDecoder(),            # conflicts with SetOf
    univ.Choice.tagSet: ChoiceDecoder(),      # conflicts with Any
    # character string types
    char.UTF8String.tagSet: UTF8StringDecoder(),
    char.NumericString.tagSet: NumericStringDecoder(),
    char.PrintableString.tagSet: PrintableStringDecoder(),
    char.TeletexString.tagSet: TeletexStringDecoder(),
    char.VideotexString.tagSet: VideotexStringDecoder(),
    char.IA5String.tagSet: IA5StringDecoder(),
    char.GraphicString.tagSet: GraphicStringDecoder(),
    char.VisibleString.tagSet: VisibleStringDecoder(),
    char.GeneralString.tagSet: GeneralStringDecoder(),
    char.UniversalString.tagSet: UniversalStringDecoder(),
    char.BMPString.tagSet: BMPStringDecoder(),
    # useful types
    useful.GeneralizedTime.tagSet: GeneralizedTimeDecoder(),
    useful.UTCTime.tagSet: UTCTimeDecoder()
    }

# Type-to-codec map for ambiguous ASN.1 types
typeMap = {
    univ.Set.typeId: SetDecoder(),
    univ.SetOf.typeId: SetOfDecoder(),
    univ.Sequence.typeId: SequenceDecoder(),
    univ.SequenceOf.typeId: SequenceOfDecoder(),
    univ.Choice.typeId: ChoiceDecoder(),
    univ.Any.typeId: AnyDecoder()
    }

( stDecodeTag, stDecodeLength, stGetValueDecoder, stGetValueDecoderByAsn1Spec,
  stGetValueDecoderByTag, stTryAsExplicitTag, stDecodeValue,
  stDumpRawValue, stErrorCondition, stStop ) = [x for x in range(10)]

class Decoder:
    defaultErrorState = stErrorCondition
#    defaultErrorState = stDumpRawValue
    defaultRawDecoder = AnyDecoder()
    def __init__(self, tagMap, typeMap={}):
        self.__tagMap = tagMap
        self.__typeMap = typeMap
        self.__endOfOctetsTagSet = eoo.endOfOctets.getTagSet()
        # Tag & TagSet objects caches
        self.__tagCache = {}
        self.__tagSetCache = {}
        
    def __call__(self, substrate, asn1Spec=None, tagSet=None,
                 length=None, state=stDecodeTag, recursiveFlag=1):
        fullSubstrate = substrate
        while state != stStop:
            if state == stDecodeTag:
                # Decode tag
                if not substrate:
                    raise error.SubstrateUnderrunError(
                        'Short octet stream on tag decoding'
                        )
                
                firstOctet = substrate[0]
                substrate = substrate[1:]
                if firstOctet in self.__tagCache:
                    lastTag = self.__tagCache[firstOctet]
                else:
                    t = oct2int(firstOctet)
                    tagClass = t&0xC0
                    tagFormat = t&0x20
                    tagId = t&0x1F
                    if tagId == 0x1F:
                        tagId = 0
                        while 1:
                            if not substrate:
                                raise error.SubstrateUnderrunError(
                                    'Short octet stream on long tag decoding'
                                    )
                            t = oct2int(substrate[0])
                            tagId = tagId << 7 | (t&0x7F)
                            substrate = substrate[1:]
                            if not t&0x80:
                                break
                    lastTag = tag.Tag(
                        tagClass=tagClass, tagFormat=tagFormat, tagId=tagId
                        )
                    if tagId < 31:
                        # cache short tags
                        self.__tagCache[firstOctet] = lastTag
                if tagSet is None:
                    if firstOctet in self.__tagSetCache:
                        tagSet = self.__tagSetCache[firstOctet]
                    else:
                        # base tag not recovered
                        tagSet = tag.TagSet((), lastTag)
                        if firstOctet in self.__tagCache:
                            self.__tagSetCache[firstOctet] = tagSet
                else:
                    tagSet = lastTag + tagSet
                state = stDecodeLength
            if state == stDecodeLength:
                # Decode length
                if not substrate:
                     raise error.SubstrateUnderrunError(
                         'Short octet stream on length decoding'
                         )
                firstOctet  = oct2int(substrate[0])
                if firstOctet == 128:
                    size = 1
                    length = -1
                elif firstOctet < 128:
                    length, size = firstOctet, 1
                else:
                    size = firstOctet & 0x7F
                    # encoded in size bytes
                    length = 0
                    lengthString = substrate[1:size+1]
                    # missing check on maximum size, which shouldn't be a
                    # problem, we can handle more than is possible
                    if len(lengthString) != size:
                        raise error.SubstrateUnderrunError(
                            '%s<%s at %s' %
                            (size, len(lengthString), tagSet)
                            )
                    for char in lengthString:
                        length = (length << 8) | oct2int(char)
                    size = size + 1
                state = stGetValueDecoder
                substrate = substrate[size:]
                if length != -1 and len(substrate) < length:
                    raise error.SubstrateUnderrunError(
                        '%d-octet short' % (length - len(substrate))
                        )
            if state == stGetValueDecoder:
                if asn1Spec is None:
                    state = stGetValueDecoderByTag
                else:
                    state = stGetValueDecoderByAsn1Spec
            #
            # There're two ways of creating subtypes in ASN.1 what influences
            # decoder operation. These methods are:
            # 1) Either base types used in or no IMPLICIT tagging has been
            #    applied on subtyping.
            # 2) Subtype syntax drops base type information (by means of
            #    IMPLICIT tagging.
            # The first case allows for complete tag recovery from substrate
            # while the second one requires original ASN.1 type spec for
            # decoding.
            #
            # In either case a set of tags (tagSet) is coming from substrate
            # in an incremental, tag-by-tag fashion (this is the case of
            # EXPLICIT tag which is most basic). Outermost tag comes first
            # from the wire.
            #            
            if state == stGetValueDecoderByTag:
                if tagSet in self.__tagMap:
                    concreteDecoder = self.__tagMap[tagSet]
                else:
                    concreteDecoder = None
                if concreteDecoder:
                    state = stDecodeValue
                else:
                    _k = tagSet[:1]
                    if _k in self.__tagMap:
                        concreteDecoder = self.__tagMap[_k]
                    else:
                        concreteDecoder = None
                    if concreteDecoder:
                        state = stDecodeValue
                    else:
                        state = stTryAsExplicitTag
            if state == stGetValueDecoderByAsn1Spec:
                if isinstance(asn1Spec, (dict, tagmap.TagMap)):
                    if tagSet in asn1Spec:
                        __chosenSpec = asn1Spec[tagSet]
                    else:
                        __chosenSpec = None
                else:
                    __chosenSpec = asn1Spec
                if __chosenSpec is not None and (
                       tagSet == __chosenSpec.getTagSet() or \
                       tagSet in __chosenSpec.getTagMap()
                       ):
                    # use base type for codec lookup to recover untagged types
                    baseTagSet = __chosenSpec.baseTagSet
                    if __chosenSpec.typeId is not None and \
                           __chosenSpec.typeId in self.__typeMap:
                        # ambiguous type
                        concreteDecoder = self.__typeMap[__chosenSpec.typeId]
                    elif baseTagSet in self.__tagMap:
                        # base type or tagged subtype
                        concreteDecoder = self.__tagMap[baseTagSet]
                    else:
                        concreteDecoder = None
                    if concreteDecoder:
                        asn1Spec = __chosenSpec
                        state = stDecodeValue
                    else:
                        state = stTryAsExplicitTag
                elif tagSet == self.__endOfOctetsTagSet:
                    concreteDecoder = self.__tagMap[tagSet]
                    state = stDecodeValue
                else:
                    state = stTryAsExplicitTag
            if state == stTryAsExplicitTag:
                if tagSet and \
                       tagSet[0][1] == tag.tagFormatConstructed and \
                       tagSet[0][0] != tag.tagClassUniversal:
                    # Assume explicit tagging
                    concreteDecoder = explicitTagDecoder
                    state = stDecodeValue
                else:                    
                    state = self.defaultErrorState
            if state == stDumpRawValue:
                concreteDecoder = self.defaultRawDecoder
                state = stDecodeValue
            if state == stDecodeValue:
                if recursiveFlag:
                    decodeFun = self
                else:
                    decodeFun = None
                if length == -1:  # indef length
                    value, substrate = concreteDecoder.indefLenValueDecoder(
                        fullSubstrate, substrate, asn1Spec, tagSet, length,
                        stGetValueDecoder, decodeFun
                        )
                else:
                    value, _substrate = concreteDecoder.valueDecoder(
                        fullSubstrate, substrate, asn1Spec, tagSet, length,
                        stGetValueDecoder, decodeFun
                        )
                    if recursiveFlag:
                        substrate = substrate[length:]
                    else:
                        substrate = _substrate
                state = stStop
            if state == stErrorCondition:
                raise error.PyAsn1Error(
                    '%r not in asn1Spec: %r' % (tagSet, asn1Spec)
                    )
        return value, substrate
            
decode = Decoder(tagMap, typeMap)

# XXX
# non-recursive decoding; return position rather than substrate
