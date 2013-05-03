"""Value related classes.

DOM Level 2 CSS CSSValue, CSSPrimitiveValue and CSSValueList are **no longer**
supported and are replaced by these new classes.
"""
__all__ = ['PropertyValue',
           'Value',
           'ColorValue',
           'DimensionValue',
           'URIValue',
           'CSSFunction',
           'CSSVariable',
           'MSValue'
           ]
__docformat__ = 'restructuredtext'
__version__ = '$Id$'

from cssutils.prodparser import *
import cssutils
from cssutils.helper import normalize, pushtoken
import colorsys
import math
import re
import xml.dom
import urlparse

class PropertyValue(cssutils.util._NewBase):
    """
    An unstructured list like holder for all values defined for a
    :class:`~cssutils.css.Property`. Contains :class:`~cssutils.css.Value`
    or subclass objects. Currently there is no access to the combinators of
    the defined values which might simply be space or comma or slash.

    You may:

    - iterate over all contained Value objects (not the separators like ``,``,
      ``/`` or `` `` though!)
    - get a Value item by index or use ``PropertyValue[index]``
    - find out the number of values defined (unstructured)
    """
    def __init__(self, cssText=None, parent=None, readonly=False):
        """
        :param cssText:
            the parsable cssText of the value
        :param readonly:
            defaults to False
        """
        super(PropertyValue, self).__init__()

        self.parent = parent
        self.wellformed = False

        if cssText is not None: # may be 0
            if isinstance(cssText, (int, float)):
                cssText = unicode(cssText) # if it is a number
            self.cssText = cssText

        self._readonly = readonly

    def __len__(self):
        return len(list(self.__items()))

    def __getitem__(self, index):
        try:
            return list(self.__items())[index]
        except IndexError:
            return None

    def __iter__(self):
        "Generator which iterates over values."
        for item in self.__items():
            yield item

    def __repr__(self):
        return u"cssutils.css.%s(%r)" % (self.__class__.__name__,
                                         self.cssText)

    def __str__(self):
        return u"<cssutils.css.%s object length=%r cssText=%r at "\
               u"0x%x>" % (self.__class__.__name__,
                           self.length, self.cssText, id(self))

    def __items(self, seq=None):
        "a generator of Value obects only, no , / or ' '"
        if seq is None:
            seq = self.seq
        return (x.value for x in seq if isinstance(x.value, Value))

    def _setCssText(self, cssText):
        if isinstance(cssText, (int, float)):
            cssText = unicode(cssText) # if it is a number
        """
        Format::

            unary_operator
              : '-' | '+'
              ;
            operator
              : '/' S* | ',' S* | /* empty */
              ;
            expr
              : term [ operator term ]*
              ;
            term
              : unary_operator?
                [ NUMBER S* | PERCENTAGE S* | LENGTH S* | EMS S* | EXS S* |
                  ANGLE S* | TIME S* | FREQ S* ]
              | STRING S* | IDENT S* | URI S* | hexcolor | function
              | UNICODE-RANGE S*
              ;
            function
              : FUNCTION S* expr ')' S*
              ;
            /*
             * There is a constraint on the color that it must
             * have either 3 or 6 hex-digits (i.e., [0-9a-fA-F])
             * after the "#"; e.g., "#000" is OK, but "#abcd" is not.
             */
            hexcolor
              : HASH S*
              ;

        :exceptions:
            - :exc:`~xml.dom.SyntaxErr`:
              Raised if the specified CSS string value has a syntax error
              (according to the attached property) or is unparsable.
            - :exc:`~xml.dom.InvalidModificationErr`:
              TODO: Raised if the specified CSS string value represents a
              different type of values than the values allowed by the CSS
              property.
            - :exc:`~xml.dom.NoModificationAllowedErr`:
              Raised if this value is readonly.
        """
        self._checkReadonly()

        # used as operator is , / or S
        nextSor = u',/'
        term = Choice(_ColorProd(self, nextSor),
                      _DimensionProd(self, nextSor),
                      _URIProd(self, nextSor),
                      _ValueProd(self, nextSor),
#                      _CalcValueProd(self, nextSor),
#                      _Rect(self, nextSor),
                      # all other functions
                      _CSSVariableProd(self, nextSor),
                      _MSValueProd(self, nextSor),
                      _CSSFunctionProd(self, nextSor)
                      )
        operator = Choice(PreDef.S(toSeq=False),
                          PreDef.char('comma', ',',
                                      toSeq=lambda t, tokens: ('operator', t[1])),
                          PreDef.char('slash', '/',
                                      toSeq=lambda t, tokens: ('operator', t[1])),
                          optional=True)
        prods = Sequence(term,
                         Sequence(# mayEnd this Sequence if whitespace
                                  operator,
                                  # TODO: only when setting via other class
                                  # used by variabledeclaration currently
                                  PreDef.char('END', ';',
                                              stopAndKeep=True,
                                              optional=True),
                                  # TODO: } and !important ends too!
                                  term,
                                  minmax=lambda: (0, None)))
        # parse
        ok, seq, store, unused = ProdParser().parse(cssText,
                                                    u'PropertyValue',
                                                    prods)
        # must be at least one value!
        ok = ok and len(list(self.__items(seq))) > 0
        if ok:
            self._setSeq(seq)
            self.wellformed = True
        else:
            self._log.error(u'PropertyValue: Unknown syntax or no value: %s' %
                            self._valuestr(cssText))

    cssText = property(lambda self: cssutils.ser.do_css_PropertyValue(self),
                       _setCssText,
                       doc="A string representation of the current value.")

    def item(self, index):
        """
        The value at position `index`. Alternatively simple use
        ``PropertyValue[index]``.

        :param index:
            the parsable cssText of the value
        :exceptions:
            - :exc:`~IndexError`:
              Raised if index if out of bounds
        """
        return self[index]

    length = property(lambda self: len(self),
                      doc=u"Number of values set.")

    value = property(lambda self: cssutils.ser.do_css_PropertyValue(self,
                                                                    valuesOnly=True),
                       doc=u"A string representation of the current value "
                           u"without any comments used for validation.")


class Value(cssutils.util._NewBase):
    """
    Represents a single CSS value. For now simple values of
    IDENT, STRING, or UNICODE-RANGE values are represented directly
    as Value objects. Other values like e.g. FUNCTIONs are represented by
    subclasses with an extended API.
    """
    IDENT = u'IDENT'
    STRING = u'STRING'
    UNICODE_RANGE = u'UNICODE-RANGE'
    URI = u'URI'

    DIMENSION = u'DIMENSION'
    NUMBER = u'NUMBER'
    PERCENTAGE = u'PERCENTAGE'

    COLOR_VALUE = u'COLOR_VALUE'
    HASH = u'HASH'

    FUNCTION = u'FUNCTION'
    VARIABLE = u'VARIABLE'

    _type = None
    _value = u''

    def __init__(self, cssText=None, parent=None, readonly=False):
        super(Value, self).__init__()

        self.parent = parent

        if cssText:
            self.cssText = cssText

    def __repr__(self):
        return u"cssutils.css.%s(%r)" % (self.__class__.__name__,
                                         self.cssText)

    def __str__(self):
        return u"<cssutils.css.%s object type=%s value=%r cssText=%r at 0x%x>"\
               % (self.__class__.__name__,
                  self.type, self.value, self.cssText,
                  id(self))

    def _setCssText(self, cssText):
        self._checkReadonly()

        prods = Choice(PreDef.hexcolor(stop=True),
                       PreDef.ident(stop=True),
                       PreDef.string(stop=True),
                       PreDef.unicode_range(stop=True),
                       )
        ok, seq, store, unused = ProdParser().parse(cssText, u'Value', prods)
        if ok:
            # only 1 value anyway!
            self._type = seq[0].type
            self._value = seq[0].value

            self._setSeq(seq)
            self.wellformed = ok

    cssText = property(lambda self: cssutils.ser.do_css_Value(self),
                       _setCssText,
                       doc=u'String value of this value.')

    type = property(lambda self: self._type, #_setType,
                    doc=u"Type of this value, for now the production type "
                        u"like e.g. `DIMENSION` or `STRING`. All types are "
                        u"defined as constants in :class:`~cssutils.css.Value`.")

    def _setValue(self, value):
        # TODO: check!
        self._value = value

    value = property(lambda self: self._value, _setValue,
                     doc=u"Actual value if possible: An int or float or else "
                         u" a string")


class ColorValue(Value):
    """
    A color value like rgb(), rgba(), hsl(), hsla() or #rgb, #rrggbb

    TODO: Color Keywords
    """
    from colors import COLORS

    type = Value.COLOR_VALUE
    # hexcolor, FUNCTION?
    _colorType = None
    _red = 0
    _green = 0
    _blue = 0
    _alpha = 0

    def __str__(self):
        return u"<cssutils.css.%s object type=%s value=%r colorType=%r "\
               u"red=%s blue=%s green=%s alpha=%s at 0x%x>"\
               % (self.__class__.__name__,
                  self.type, self.value,
                  self.colorType, self.red, self.green, self.blue, self.alpha,
                  id(self))

    def _setCssText(self, cssText):
        self._checkReadonly()
        types = self._prods # rename!

        component = Choice(PreDef.unary(toSeq=lambda t, tokens: (t[0],
                            DimensionValue(pushtoken(t, tokens),
                            parent=self)
                           )),
                           PreDef.number(toSeq=lambda t, tokens: (t[0],
                            DimensionValue(pushtoken(t, tokens),
                            parent=self)
                           )),
                           PreDef.percentage(toSeq=lambda t, tokens: (t[0],
                            DimensionValue(pushtoken(t, tokens),
                            parent=self)
                           ))
                   )
        noalp = Sequence(Prod(name='FUNCTION',
                              match=lambda t, v: t == types.FUNCTION and
                                                 v in (u'rgb(', u'hsl('),
                              toSeq=lambda t, tokens: (t[0], normalize(t[1]))),
                          component,
                          Sequence(PreDef.comma(),
                                   component,
                                   minmax=lambda: (2, 2)
                                   ),
                          PreDef.funcEnd(stop=True)
                          )
        witha = Sequence(Prod(name='FUNCTION',
                              match=lambda t, v: t == types.FUNCTION and
                                                 v in (u'rgba(', u'hsla('),
                              toSeq=lambda t, tokens: (t[0],
                                 normalize(t[1]))
                              ),
                          component,
                          Sequence(PreDef.comma(),
                                   component,
                                   minmax=lambda: (3, 3)
                                   ),
                          PreDef.funcEnd(stop=True)
                          )
        namedcolor = Prod(name='Named Color',
                     match=lambda t, v: t == 'IDENT' and (
                                        normalize(v) in self.COLORS.keys()
                                        ),
                     stop=True)

        prods = Choice(PreDef.hexcolor(stop=True),
                       namedcolor,
                       noalp,
                       witha)

        ok, seq, store, unused = ProdParser().parse(cssText,
                                                    self.type,
                                                    prods)
        if ok:
            t, v = seq[0].type, seq[0].value
            if u'IDENT' == t:
                rgba = self.COLORS[normalize(v)]
            if u'HASH' == t:
                if len(v) == 4:
                    # HASH #rgb
                    rgba = (int(2*v[1], 16),
                            int(2*v[2], 16),
                            int(2*v[3], 16),
                            1.0)
                else:
                    # HASH #rrggbb
                    rgba = (int(v[1:3], 16),
                            int(v[3:5], 16),
                            int(v[5:7], 16),
                            1.0)

            elif u'FUNCTION' == t:
                functiontype, raw, check = None, [], u''
                HSL = False

                for item in seq:
                    try:
                        type_ = item.value.type
                    except AttributeError, e:
                        # type of function, e.g. rgb(
                        if item.type == 'FUNCTION':
                            functiontype = item.value
                            HSL = functiontype in (u'hsl(', u'hsla(')
                        continue

                    # save components
                    if type_ == Value.NUMBER:
                        raw.append(item.value.value)
                        check += u'N'
                    elif type_ == Value.PERCENTAGE:
                        if HSL:
                            # save as percentage fraction
                            raw.append(item.value.value / 100.0)
                        else:
                            # save as real value of percentage of 255
                            raw.append(int(255 * item.value.value / 100))
                        check += u'P'

                if HSL:
                    # convert to rgb
                    # h is 360 based (circle)
                    h, s, l = raw[0] / 360.0, raw[1], raw[2]
                    # ORDER h l s !!!
                    r, g, b = colorsys.hls_to_rgb(h, l, s)
                    # back to 255 based
                    rgba = [int(round(r*255)),
                            int(round(g*255)),
                            int(round(b*255))]

                    if len(raw) > 3:
                        rgba.append(raw[3])

                else:
                    # rgb, rgba
                    rgba = raw

                if len(rgba) < 4:
                    rgba.append(1.0)

                # validate
                checks = {u'rgb(': ('NNN', 'PPP'),
                         u'rgba(': ('NNNN', 'PPPN'),
                         u'hsl(': ('NPP',),
                         u'hsla(': ('NPPN',)
                         }
                if check not in checks[functiontype]:
                    self._log.error(u'ColorValue has invalid %s) parameters: '
                                    u'%s (N=Number, P=Percentage)' %
                                    (functiontype, check))

            self._colorType = t
            self._red, self._green, self._blue, self._alpha = tuple(rgba)
            self._setSeq(seq)
            self.wellformed = ok

    cssText = property(lambda self: cssutils.ser.do_css_ColorValue(self),
                       _setCssText,
                       doc=u"String value of this value.")

    value = property(lambda self: cssutils.ser.do_css_CSSFunction(self, True),
                     doc=u'Same as cssText but without comments.')

    type = property(lambda self: Value.COLOR_VALUE,
                    doc=u"Type is fixed to Value.COLOR_VALUE.")

    def _getName(self):
        for n, v in self.COLORS.items():
            if v == (self.red, self.green, self.blue, self.alpha):
                return n

    colorType = property(lambda self: self._colorType,
                    doc=u"IDENT (red), HASH (#f00) or FUNCTION (rgb(255, 0, 0).")

    name = property(_getName,
                    doc=u'Name of the color if known (in ColorValue.COLORS) '
                        u'else None')

    red = property(lambda self: self._red,
                   doc=u'red part as integer between 0 and 255')
    green = property(lambda self: self._green,
                     doc=u'green part as integer between 0 and 255')
    blue = property(lambda self: self._blue,
                    doc=u'blue part as integer between 0 and 255')
    alpha = property(lambda self: self._alpha,
                     doc=u'alpha part as float between 0.0 and 1.0')

class DimensionValue(Value):
    """
    A numerical value with an optional dimenstion like e.g. "px" or "%".

    Covers DIMENSION, PERCENTAGE or NUMBER values.
    """
    __reNumDim = re.compile(ur'^(\d*\.\d+|\d+)(.*)$', re.I | re.U | re.X)
    _dimension = None
    _sign = None

    def __str__(self):
        return u"<cssutils.css.%s object type=%s value=%r dimension=%r cssText=%r at 0x%x>"\
               % (self.__class__.__name__,
                  self.type, self.value, self.dimension, self.cssText,
                  id(self))

    def _setCssText(self, cssText):
        self._checkReadonly()

        prods = Sequence(PreDef.unary(),
                         Choice(PreDef.dimension(stop=True),
                                PreDef.number(stop=True),
                                PreDef.percentage(stop=True)
                                )
                         )
        ok, seq, store, unused = ProdParser().parse(cssText,
                                                    u'DimensionValue',
                                                    prods)
        if ok:
            sign = val = u''
            dim = type_ = None

            # find
            for item in seq:
                if item.value in u'+-':
                    sign = item.value
                else:
                    type_ = item.type

                    # number + optional dim
                    v, d = self.__reNumDim.findall(
                                normalize(item.value))[0]
                    if u'.' in v:
                        val = float(sign + v)
                    else:
                        val = int(sign + v)
                    if d:
                        dim = d

            self._sign = sign
            self._value = val
            self._dimension = dim
            self._type = type_

            self._setSeq(seq)
            self.wellformed = ok

    cssText = property(lambda self: cssutils.ser.do_css_Value(self),
                       _setCssText,
                       doc=u"String value of this value including dimension.")

    dimension = property(lambda self: self._dimension, #_setValue,
                         doc=u"Dimension if a DIMENSION or PERCENTAGE value, "
                             u"else None")
class URIValue(Value):
    """
    An URI value like ``url(example.png)``.
    """
    _type = Value.URI
    _uri = Value._value

    def __str__(self):
        return u"<cssutils.css.%s object type=%s value=%r uri=%r cssText=%r at 0x%x>"\
               % (self.__class__.__name__,
                  self.type, self.value, self.uri, self.cssText,
                  id(self))

    def _setCssText(self, cssText):
        self._checkReadonly()

        prods = Sequence(PreDef.uri(stop=True))

        ok, seq, store, unused = ProdParser().parse(cssText, u'URIValue', prods)
        if ok:
            # only 1 value only anyway
            self._type = seq[0].type
            self._value = seq[0].value

            self._setSeq(seq)
            self.wellformed = ok

    cssText = property(lambda self: cssutils.ser.do_css_Value(self),
                       _setCssText,
                       doc=u'String value of this value.')

    def _setUri(self, uri):
        # TODO: check?
        self._value = uri

    uri = property(lambda self: self._value, _setUri,
                         doc=u"Actual URL without delimiters or the empty string")

    def absoluteUri(self):
        """Actual URL, made absolute if possible, else same as `uri`."""
        # Ancestry: PropertyValue, Property, CSSStyleDeclaration, CSSStyleRule,
        # CSSStyleSheet
        try:
            # TODO: better way?
            styleSheet = self.parent.parent.parent.parentRule.parentStyleSheet
        except AttributeError, e:
            return self.uri
        else:
            return urlparse.urljoin(styleSheet.href, self.uri)

    absoluteUri = property(absoluteUri, doc=absoluteUri.__doc__)


class CSSFunction(Value):
    """
    A function value.
    """
    _functionName = 'Function'

    def _productions(self):
        """Return definition used for parsing."""
        types = self._prods # rename!

        itemProd = Choice(_ColorProd(self),
                          _DimensionProd(self),
                          _URIProd(self),
                          _ValueProd(self),
                          #_CalcValueProd(self),
                          _CSSVariableProd(self),
                          _CSSFunctionProd(self)
                          )
        funcProds = Sequence(Prod(name='FUNCTION',
                                  match=lambda t, v: t == types.FUNCTION,
                                  toSeq=lambda t, tokens: (t[0],
                                                           normalize(t[1]))),
                             Choice(Sequence(itemProd,
                                             Sequence(PreDef.comma(),
                                                      itemProd,
                                                      minmax=lambda: (0, None)),
                                             PreDef.funcEnd(stop=True)),
                                    PreDef.funcEnd(stop=True))
         )
        return funcProds

    def _setCssText(self, cssText):
        self._checkReadonly()
        ok, seq, store, unused = ProdParser().parse(cssText,
                                                    self.type,
                                                    self._productions())
        if ok:
            self._setSeq(seq)
            self.wellformed = ok

    cssText = property(lambda self: cssutils.ser.do_css_CSSFunction(self),
                       _setCssText,
                       doc=u"String value of this value.")

    value = property(lambda self: cssutils.ser.do_css_CSSFunction(self, True),
                     doc=u'Same as cssText but without comments.')

    type = property(lambda self: Value.FUNCTION,
                    doc=u"Type is fixed to Value.FUNCTION.")

class MSValue(CSSFunction):
    """An IE specific Microsoft only function value which is much looser
    in what is syntactically allowed."""
    _functionName = 'MSValue'

    def _productions(self):
        """Return definition used for parsing."""
        types = self._prods # rename!

        func = Prod(name='MSValue-Sub',
                    match=lambda t, v: t == self._prods.FUNCTION,
                    toSeq=lambda t, tokens: (MSValue._functionName,
                                     MSValue(pushtoken(t,
                                                                       tokens
                                                                       ),
                                            parent=self
                                            )
                                         )
                    )


        funcProds = Sequence(Prod(name='FUNCTION',
                                  match=lambda t, v: t == types.FUNCTION,
                                  toSeq=lambda t, tokens: (t[0], t[1])
                                  ),
                             Sequence(Choice(_ColorProd(self),
                                             _DimensionProd(self),
                                             _URIProd(self),
                                             _ValueProd(self),
                                             _MSValueProd(self),
                                             #_CalcValueProd(self),
                                             _CSSVariableProd(self),
                                             func,
                                             #_CSSFunctionProd(self),
                                             Prod(name='MSValuePart',
                                                  match=lambda t, v: v != u')',
                                                  toSeq=lambda t, tokens: (t[0], t[1])
                                                  )
                                             ),
                                      minmax=lambda: (0, None)
                                      ),
                             PreDef.funcEnd(stop=True)
                             )
        return funcProds

    def _setCssText(self, cssText):
        super(MSValue, self)._setCssText(cssText)

    cssText = property(lambda self: cssutils.ser.do_css_MSValue(self),
                       _setCssText,
                       doc=u"String value of this value.")


class CSSVariable(CSSFunction):
    """The CSSVariable represents a CSS variables like ``var(varname)``.

    A variable has a (nonnormalized!) `name` and a `value` which is
    tried to be resolved from any available CSSVariablesRule definition.
    """
    _functionName = 'CSSVariable'
    _name = None

    def __str__(self):
        return u"<cssutils.css.%s object name=%r value=%r at 0x%x>" % (
                self.__class__.__name__, self.name, self.value, id(self))

    def _setCssText(self, cssText):
        self._checkReadonly()

        types = self._prods # rename!
        prods = Sequence(Prod(name='var',
                                  match=lambda t, v: t == types.FUNCTION and
                                        normalize(v) == u'var('
                             ),
                             PreDef.ident(toStore='ident'),
                             PreDef.funcEnd(stop=True))

        # store: name of variable
        store = {'ident': None}
        ok, seq, store, unused = ProdParser().parse(cssText,
                                                    u'CSSVariable',
                                                    prods)
        if ok:
            self._name = store['ident'].value
            self._setSeq(seq)
            self.wellformed = ok

    cssText = property(lambda self: cssutils.ser.do_css_CSSVariable(self),
                       _setCssText, doc=u"String representation of variable.")

    # TODO: writable? check if var (value) available?
    name = property(lambda self: self._name,
                    doc=u"The name identifier of this variable referring to "
                        u"a value in a "
                        u":class:`cssutils.css.CSSVariablesDeclaration`.")

    type = property(lambda self: Value.VARIABLE,
                    doc=u"Type is fixed to Value.VARIABLE.")

    def _getValue(self):
        "Find contained sheet and @variables there"
        rel = self
        while True:
            # find node which has parentRule to get to StyleSheet
            if hasattr(rel, 'parent'):
                rel = rel.parent
            else:
                break
        try:
            variables = rel.parentRule.parentStyleSheet.variables
        except AttributeError:
            return None
        else:
            try:
                return variables[self.name]
            except KeyError:
                return None

    value = property(_getValue,
                     doc=u'The resolved actual value or None.')


# helper for productions
def _ValueProd(parent, nextSor=False):
    return Prod(name='Value',
                match=lambda t, v: t in ('IDENT', 'STRING', 'UNICODE-RANGE'),
                nextSor = nextSor,
                toSeq=lambda t, tokens: ('Value', Value(
                                            pushtoken(t,
                                                                      tokens),
                                         parent=parent)
                                         )
                )


def _DimensionProd(parent, nextSor=False):
    return Prod(name='Dimension',
                match=lambda t, v: t in (u'DIMENSION',
                                         u'NUMBER',
                                         u'PERCENTAGE') or v in u'+-',
                nextSor = nextSor,
                toSeq=lambda t, tokens: (t[0], DimensionValue(
                                            pushtoken(t,
                                                                      tokens),
                                         parent=parent)
                                         )
                )

def _URIProd(parent, nextSor=False):
    return Prod(name='URIValue',
                match=lambda t, v: t == 'URI',
                nextSor = nextSor,
                toSeq=lambda t, tokens: ('URIValue', URIValue(
                                            pushtoken(t,
                                                                      tokens),
                                         parent=parent)
                                         )
                )

reHexcolor = re.compile(r'^\#(?:[0-9abcdefABCDEF]{3}|[0-9abcdefABCDEF]{6})$')

def _ColorProd(parent, nextSor=False):
    return Prod(name='ColorValue',
                match=lambda t, v:
                                   (t == 'HASH' and
                                    reHexcolor.match(v)
                                    ) or
                                   (t == 'FUNCTION' and
                                    normalize(v) in (u'rgb(',
                                                     u'rgba(',
                                                     u'hsl(',
                                                     u'hsla(')
                                    ) or
                                   (t == 'IDENT' and
                                    normalize(v) in ColorValue.COLORS.keys()
                                    ),
                nextSor = nextSor,
                toSeq=lambda t, tokens: ('ColorValue', ColorValue(
                                            pushtoken(t,
                                                                      tokens),
                                         parent=parent)
                                         )
                )

def _CSSFunctionProd(parent, nextSor=False):
    return PreDef.function(nextSor=nextSor,
                           toSeq=lambda t, tokens: (CSSFunction._functionName,
                                                    CSSFunction(
                                pushtoken(t, tokens),
                                parent=parent)
                                )
                           )

def _CSSVariableProd(parent, nextSor=False):
    return PreDef.variable(nextSor=nextSor,
                           toSeq=lambda t, tokens: (CSSVariable._functionName,
                                                    CSSVariable(
                                pushtoken(t, tokens),
                                parent=parent)
                                                    )
                           )

def _MSValueProd(parent, nextSor=False):
    return Prod(name=MSValue._functionName,
                match=lambda t, v: (#t == self._prods.FUNCTION and (
                    normalize(v) in (u'expression(',
                                                     u'alpha(',
                                                     u'blur(',
                                                     u'chroma(',
                                                     u'dropshadow(',
                                                     u'fliph(',
                                                     u'flipv(',
                                                     u'glow(',
                                                     u'gray(',
                                                     u'invert(',
                                                     u'mask(',
                                                     u'shadow(',
                                                     u'wave(',
                                                     u'xray(') or
                    v.startswith(u'progid:DXImageTransform.Microsoft.')
                    ),
                nextSor=nextSor,
                toSeq=lambda t, tokens: (MSValue._functionName,
                                         MSValue(pushtoken(t,
                                                                           tokens
                                                                           ),
                                                 parent=parent
                                                 )
                                         )
                )
