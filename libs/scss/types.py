from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import colorsys
import operator

import six

from scss.cssdefs import COLOR_LOOKUP, COLOR_NAMES, ZEROABLE_UNITS, convert_units_to_base_units, cancel_base_units, count_base_units
from scss.util import escape


################################################################################
# pyScss data types:

class Value(object):
    is_null = False
    sass_type_name = u'unknown'

    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.value))

    # Sass values are all true, except for booleans and nulls
    def __bool__(self):
        return True

    def __nonzero__(self):
        # Py 2's name for __bool__
        return self.__bool__()

    # All Sass scalars also act like one-element spaced lists
    use_comma = False

    def __iter__(self):
        return iter((self,))

    def __len__(self):
        return 1

    def __getitem__(self, key):
        if key not in (-1, 0):
            raise IndexError(key)

        return self

    def __contains__(self, item):
        return self == item

    ### NOTE: From here on down, the operators are exposed to Sass code and
    ### thus should ONLY return Sass types

    # Reasonable default for equality
    def __eq__(self, other):
        return Boolean(
            type(self) == type(other) and self.value == other.value)

    def __ne__(self, other):
        return Boolean(not self.__eq__(other))

    # Only numbers support ordering
    def __lt__(self, other):
        raise TypeError("Can't compare %r with %r" % (self, other))

    def __le__(self, other):
        raise TypeError("Can't compare %r with %r" % (self, other))

    def __gt__(self, other):
        raise TypeError("Can't compare %r with %r" % (self, other))

    def __ge__(self, other):
        raise TypeError("Can't compare %r with %r" % (self, other))

    # Math ops
    def __add__(self, other):
        # Default behavior is to treat both sides like strings
        if isinstance(other, String):
            return String(self.render() + other.value, quotes=other.quotes)
        return String(self.render() + other.render())

    def __sub__(self, other):
        # Default behavior is to treat the whole expression like one string
        return String(self.render() + "-" + other.render())

    def __div__(self, other):
        return String(self.render() + "/" + other.render())

    # Sass types have no notion of floor vs true division
    def __truediv__(self, other):
        return self.__div__(other)

    def __floordiv__(self, other):
        return self.__div__(other)

    def __mul__(self, other):
        return NotImplemented

    def __pos__(self):
        return String("+" + self.render())

    def __neg__(self):
        return String("-" + self.render())

    def to_dict(self):
        """Return the Python dict equivalent of this map.

        If this type can't be expressed as a map, raise.
        """
        return dict(self.to_pairs())

    def to_pairs(self):
        """Return the Python list-of-tuples equivalent of this map.  Note that
        this is different from ``self.to_dict().items()``, because Sass maps
        preserve order.

        If this type can't be expressed as a map, raise.
        """
        raise ValueError("Not a map: {0!r}".format(self))

    def render(self, compress=False):
        return self.__str__()


class Null(Value):
    is_null = True
    sass_type_name = u'null'

    def __init__(self, value=None):
        pass

    def __str__(self):
        return self.sass_type_name

    def __repr__(self):
        return "<%s()>" % (self.__class__.__name__,)

    def __hash__(self):
        return hash(None)

    def __bool__(self):
        return False

    def __eq__(self, other):
        return Boolean(isinstance(other, Null))

    def __ne__(self, other):
        return Boolean(not self.__eq__(other))

    def render(self, compress=False):
        return self.sass_type_name


class Undefined(Null):
    sass_type_name = u'undefined'

    def __init__(self, value=None):
        pass

    def __add__(self, other):
        return self

    def __radd__(self, other):
        return self

    def __sub__(self, other):
        return self

    def __rsub__(self, other):
        return self

    def __div__(self, other):
        return self

    def __rdiv__(self, other):
        return self

    def __truediv__(self, other):
        return self

    def __rtruediv__(self, other):
        return self

    def __floordiv__(self, other):
        return self

    def __rfloordiv__(self, other):
        return self

    def __mul__(self, other):
        return self

    def __rmul__(self, other):
        return self

    def __pos__(self):
        return self

    def __neg__(self):
        return self


class Boolean(Value):
    sass_type_name = u'bool'

    def __init__(self, value):
        self.value = bool(value)

    def __str__(self):
        return 'true' if self.value else 'false'

    def __hash__(self):
        return hash(self.value)

    def __bool__(self):
        return self.value

    def render(self, compress=False):
        if self.value:
            return 'true'
        else:
            return 'false'


class Number(Value):
    sass_type_name = u'number'

    def __init__(self, amount, unit=None, unit_numer=(), unit_denom=()):
        if isinstance(amount, Number):
            assert not unit and not unit_numer and not unit_denom
            self.value = amount.value
            self.unit_numer = amount.unit_numer
            self.unit_denom = amount.unit_denom
            return

        if not isinstance(amount, (int, float)):
            raise TypeError("Expected number, got %r" % (amount,))

        if unit is not None:
            unit_numer = unit_numer + (unit.lower(),)

        # Cancel out any convertable units on the top and bottom
        numerator_base_units = count_base_units(unit_numer)
        denominator_base_units = count_base_units(unit_denom)

        # Count which base units appear both on top and bottom
        cancelable_base_units = {}
        for unit, count in numerator_base_units.items():
            cancelable_base_units[unit] = min(
                count, denominator_base_units.get(unit, 0))

        # Actually remove the units
        numer_factor, unit_numer = cancel_base_units(unit_numer, cancelable_base_units)
        denom_factor, unit_denom = cancel_base_units(unit_denom, cancelable_base_units)

        # And we're done
        self.unit_numer = tuple(unit_numer)
        self.unit_denom = tuple(unit_denom)
        self.value = amount * (numer_factor / denom_factor)

    def __repr__(self):
        full_unit = ' * '.join(self.unit_numer)
        if self.unit_denom:
            full_unit += ' / '
            full_unit += ' * '.join(self.unit_denom)

            if full_unit:
                full_unit = ' ' + full_unit

        return '<%s(%r%s)>' % (self.__class__.__name__, self.value, full_unit)

    def __hash__(self):
        return hash((self.value, self.unit_numer, self.unit_denom))

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __pos__(self):
        return self

    def __neg__(self):
        return self * Number(-1)

    def __str__(self):
        return self.render()

    def __eq__(self, other):
        if not isinstance(other, Number):
            return Boolean(False)
        return self._compare(other, operator.__eq__, soft_fail=True)

    def __lt__(self, other):
        return self._compare(other, operator.__lt__)

    def __le__(self, other):
        return self._compare(other, operator.__le__)

    def __gt__(self, other):
        return self._compare(other, operator.__gt__)

    def __ge__(self, other):
        return self._compare(other, operator.__ge__)

    def _compare(self, other, op, soft_fail=False):
        if not isinstance(other, Number):
            raise TypeError("Can't compare %r and %r" % (self, other))

        # A unitless operand is treated as though it had the other operand's
        # units, and zero values can cast to anything, so in both cases the
        # units can be ignored
        if (self.is_unitless or other.is_unitless or
                self.value == 0 or other.value == 0):
            left = self
            right = other
        else:
            left = self.to_base_units()
            right = other.to_base_units()

            if left.unit_numer != right.unit_numer or left.unit_denom != right.unit_denom:
                if soft_fail:
                    # Used for equality only, where == should never fail
                    return Boolean(False)
                else:
                    raise ValueError("Can't reconcile units: %r and %r" % (self, other))

        return Boolean(op(round(left.value, 5), round(right.value, 5)))

    def __pow__(self, exp):
        if not isinstance(exp, Number):
            raise TypeError("Can't raise %r to power %r" % (self, exp))
        if not exp.is_unitless:
            raise TypeError("Exponent %r cannot have units" % (exp,))

        if self.is_unitless:
            return Number(self.value ** exp.value)

        # Units can only be exponentiated to integral powers -- what's the
        # square root of 'px'?  (Well, it's sqrt(px), but supporting that is
        # a bit out of scope.)
        if exp.value != int(exp.value):
            raise ValueError("Can't raise units of %r to non-integral power %r" % (self, exp))

        return Number(
            self.value ** int(exp.value),
            unit_numer=self.unit_numer * int(exp.value),
            unit_denom=self.unit_denom * int(exp.value),
        )

    def __mul__(self, other):
        if not isinstance(other, Number):
            return NotImplemented

        amount = self.value * other.value
        numer = self.unit_numer + other.unit_numer
        denom = self.unit_denom + other.unit_denom

        return Number(amount, unit_numer=numer, unit_denom=denom)

    def __div__(self, other):
        if not isinstance(other, Number):
            return NotImplemented

        amount = self.value / other.value
        numer = self.unit_numer + other.unit_denom
        denom = self.unit_denom + other.unit_numer

        return Number(amount, unit_numer=numer, unit_denom=denom)

    def __add__(self, other):
        # Numbers auto-cast to strings when added to other strings
        if isinstance(other, String):
            return String(self.render(), quotes=None) + other

        return self._add_sub(other, operator.add)

    def __sub__(self, other):
        return self._add_sub(other, operator.sub)

    def _add_sub(self, other, op):
        """Implements both addition and subtraction."""
        if not isinstance(other, Number):
            return NotImplemented

        # If either side is unitless, inherit the other side's units.  Skip all
        # the rest of the conversion math, too.
        if self.is_unitless or other.is_unitless:
            return Number(
                op(self.value, other.value),
                unit_numer=self.unit_numer or other.unit_numer,
                unit_denom=self.unit_denom or other.unit_denom,
            )

        # Likewise, if either side is zero, it can auto-cast to any units
        if self.value == 0:
            return Number(
                op(self.value, other.value),
                unit_numer=other.unit_numer,
                unit_denom=other.unit_denom,
            )
        elif other.value == 0:
            return Number(
                op(self.value, other.value),
                unit_numer=self.unit_numer,
                unit_denom=self.unit_denom,
            )

        # Reduce both operands to the same units
        left = self.to_base_units()
        right = other.to_base_units()

        if left.unit_numer != right.unit_numer or left.unit_denom != right.unit_denom:
            raise ValueError("Can't reconcile units: %r and %r" % (self, other))

        new_amount = op(left.value, right.value)

        # Convert back to the left side's units
        if left.value != 0:
            new_amount = new_amount * self.value / left.value

        return Number(new_amount, unit_numer=self.unit_numer, unit_denom=self.unit_denom)

    ### Helper methods, mostly used internally

    def to_base_units(self):
        """Convert to a fixed set of "base" units.  The particular units are
        arbitrary; what's important is that they're consistent.

        Used for addition and comparisons.
        """
        # Convert to "standard" units, as defined by the conversions dict above
        amount = self.value

        numer_factor, numer_units = convert_units_to_base_units(self.unit_numer)
        denom_factor, denom_units = convert_units_to_base_units(self.unit_denom)

        return Number(
            amount * numer_factor / denom_factor,
            unit_numer=numer_units,
            unit_denom=denom_units,
        )

    ### Utilities for public consumption

    @classmethod
    def wrap_python_function(cls, fn):
        """Wraps an unary Python math function, translating the argument from
        Sass to Python on the way in, and vice versa for the return value.

        Used to wrap simple Python functions like `ceil`, `floor`, etc.
        """
        def wrapped(sass_arg):
            # TODO enforce no units for trig?
            python_arg = sass_arg.value
            python_ret = fn(python_arg)
            sass_ret = cls(
                python_ret,
                unit_numer=sass_arg.unit_numer,
                unit_denom=sass_arg.unit_denom)
            return sass_ret

        return wrapped

    def to_python_index(self, length, check_bounds=True, circular=False):
        """Return a plain Python integer appropriate for indexing a sequence of
        the given length.  Raise if this is impossible for any reason
        whatsoever.
        """
        if not self.is_unitless:
            raise ValueError("Index cannot have units: {0!r}".format(self))

        ret = int(self.value)
        if ret != self.value:
            raise ValueError("Index must be an integer: {0!r}".format(ret))

        if ret == 0:
            raise ValueError("Index cannot be zero")

        if check_bounds and not circular and abs(ret) > length:
            raise ValueError("Index {0!r} out of bounds for length {1}".format(ret, length))

        if ret > 0:
            ret -= 1

        if circular:
            ret = ret % length

        return ret

    @property
    def has_simple_unit(self):
        """Returns True iff the unit is expressible in CSS, i.e., has no
        denominator and at most one unit in the numerator.
        """
        return len(self.unit_numer) <= 1 and not self.unit_denom

    def is_simple_unit(self, unit):
        """Return True iff the unit is simple (as above) and matches the given
        unit.
        """
        if self.unit_denom or len(self.unit_numer) > 1:
            return False

        if not self.unit_numer:
            # Empty string historically means no unit
            return unit == ''

        return self.unit_numer[0] == unit

    @property
    def is_unitless(self):
        return not self.unit_numer and not self.unit_denom

    def render(self, compress=False):
        if not self.has_simple_unit:
            raise ValueError("Can't express compound units in CSS: %r" % (self,))

        if self.unit_numer:
            unit = self.unit_numer[0]
        else:
            unit = ''

        value = self.value
        if compress and unit in ZEROABLE_UNITS and value == 0:
            return '0'

        if value == 0:  # -0.0 is plain 0
            value = 0

        val = "%0.05f" % round(value, 5)
        val = val.rstrip('0').rstrip('.')

        if compress and val.startswith('0.'):
            # Strip off leading zero when compressing
            val = val[1:]

        return val + unit


class List(Value):
    """A list of other values.  May be delimited by commas or spaces.

    Lists of one item don't make much sense in CSS, but can exist in Sass.  Use ......

    Lists may also contain zero items, but these are forbidden from appearing
    in CSS output.
    """

    sass_type_name = u'list'

    def __init__(self, iterable, separator=None, use_comma=None, is_literal=False):
        if isinstance(iterable, List):
            iterable = iterable.value

        if not isinstance(iterable, (list, tuple)):
            raise TypeError("Expected list, got %r" % (iterable,))

        self.value = list(iterable)

        for item in self.value:
            if not isinstance(item, Value):
                raise TypeError("Expected a Sass type, got %r" % (item,))

        # TODO remove separator argument entirely
        if use_comma is None:
            self.use_comma = separator == ","
        else:
            self.use_comma = use_comma

        self.is_literal = is_literal

    @classmethod
    def maybe_new(cls, values, use_comma=True):
        """If `values` contains only one item, return that item.  Otherwise,
        return a List as normal.
        """
        if len(values) == 1:
            return values[0]
        else:
            return cls(values, use_comma=use_comma)

    def maybe(self):
        """If this List contains only one item, return it.  Otherwise, return
        the List.
        """
        if len(self.value) == 1:
            return self.value[0]
        else:
            return self

    @classmethod
    def from_maybe(cls, values, use_comma=True):
        """If `values` appears to not be a list, return a list containing it.
        Otherwise, return a List as normal.
        """
        if values is None:
            values = []
        return values

    @classmethod
    def from_maybe_starargs(cls, args, use_comma=True):
        """If `args` has one element which appears to be a list, return it.
        Otherwise, return a list as normal.

        Mainly used by Sass function implementations that predate `...`
        support, so they can accept both a list of arguments and a single list
        stored in a variable.
        """
        if len(args) == 1:
            if isinstance(args[0], cls):
                return args[0]
            elif isinstance(args[0], (list, tuple)):
                return cls(args[0], use_comma=use_comma)

        return cls(args, use_comma=use_comma)

    def __repr__(self):
        return "<List(%r, %r)>" % (
            self.value,
            self.delimiter(compress=True),
        )

    def __hash__(self):
        return hash((tuple(self.value), self.use_comma))

    def delimiter(self, compress=False):
        if self.use_comma:
            if compress:
                return ','
            else:
                return ', '
        else:
            return ' '

    def __len__(self):
        return len(self.value)

    def __str__(self):
        return self.render()

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    def to_pairs(self):
        pairs = []
        for item in self:
            if len(item) != 2:
                return super(List, self).to_pairs()

            pairs.append(tuple(item))

        return pairs

    def render(self, compress=False):
        if not self.value:
            raise ValueError("Can't render empty list as CSS")

        delim = self.delimiter(compress)

        if self.is_literal:
            value = self.value
        else:
            # Non-literal lists have nulls stripped
            value = [item for item in self.value if not item.is_null]
            # Non-empty lists containing only nulls become nothing, just like
            # single nulls
            if not value:
                return ''

        return delim.join(
            item.render(compress=compress)
            for item in value
        )

    # DEVIATION: binary ops on lists and scalars act element-wise
    def __add__(self, other):
        if isinstance(other, List):
            max_list, min_list = (self, other) if len(self) > len(other) else (other, self)
            return List([item + max_list[i] for i, item in enumerate(min_list)], use_comma=self.use_comma)

        elif isinstance(other, String):
            # UN-DEVIATION: adding a string should fall back to canonical
            # behavior of string addition
            return super(List, self).__add__(other)

        else:
            return List([item + other for item in self], use_comma=self.use_comma)

    def __sub__(self, other):
        if isinstance(other, List):
            max_list, min_list = (self, other) if len(self) > len(other) else (other, self)
            return List([item - max_list[i] for i, item in enumerate(min_list)], use_comma=self.use_comma)

        return List([item - other for item in self], use_comma=self.use_comma)

    def __mul__(self, other):
        if isinstance(other, List):
            max_list, min_list = (self, other) if len(self) > len(other) else (other, self)
            max_list, min_list = (self, other) if len(self) > len(other) else (other, self)
            return List([item * max_list[i] for i, item in enumerate(min_list)], use_comma=self.use_comma)

        return List([item * other for item in self], use_comma=self.use_comma)

    def __div__(self, other):
        if isinstance(other, List):
            max_list, min_list = (self, other) if len(self) > len(other) else (other, self)
            return List([item / max_list[i] for i, item in enumerate(min_list)], use_comma=self.use_comma)

        return List([item / other for item in self], use_comma=self.use_comma)

    def __pos__(self):
        return self

    def __neg__(self):
        return List([-item for item in self], use_comma=self.use_comma)


def _constrain(value, lb=0, ub=1):
    """Helper for Color constructors.  Constrains a value to a range."""
    if value < lb:
        return lb
    elif value > ub:
        return ub
    else:
        return value


class Color(Value):
    sass_type_name = u'color'
    original_literal = None

    def __init__(self, tokens):
        self.tokens = tokens
        self.value = (0, 0, 0, 1)
        if tokens is None:
            self.value = (0, 0, 0, 1)
        elif isinstance(tokens, Color):
            self.value = tokens.value
        else:
            raise TypeError("Can't make Color from %r" % (tokens,))

    ### Alternate constructors

    @classmethod
    def from_rgb(cls, red, green, blue, alpha=1.0, original_literal=None):
        red = _constrain(red)
        green = _constrain(green)
        blue = _constrain(blue)
        alpha = _constrain(alpha)

        self = cls.__new__(cls)  # TODO
        self.tokens = None
        # TODO really should store these things internally as 0-1, but can't
        # until stuff stops examining .value directly
        self.value = (red * 255.0, green * 255.0, blue * 255.0, alpha)

        if original_literal is not None:
            self.original_literal = original_literal

        return self

    @classmethod
    def from_hsl(cls, hue, saturation, lightness, alpha=1.0):
        hue = _constrain(hue)
        saturation = _constrain(saturation)
        lightness = _constrain(lightness)
        alpha = _constrain(alpha)

        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        return cls.from_rgb(r, g, b, alpha)

    @classmethod
    def from_hex(cls, hex_string, literal=False):
        if not hex_string.startswith('#'):
            raise ValueError("Expected #abcdef, got %r" % (hex_string,))

        if literal:
            original_literal = hex_string
        else:
            original_literal = None

        hex_string = hex_string[1:]

        # Always include the alpha channel
        if len(hex_string) == 3:
            hex_string += 'f'
        elif len(hex_string) == 6:
            hex_string += 'ff'

        # Now there should be only two possibilities.  Normalize to a list of
        # two hex digits
        if len(hex_string) == 4:
            chunks = [ch * 2 for ch in hex_string]
        elif len(hex_string) == 8:
            chunks = [
                hex_string[0:2], hex_string[2:4], hex_string[4:6], hex_string[6:8]
            ]

        rgba = [int(ch, 16) / 255 for ch in chunks]
        return cls.from_rgb(*rgba, original_literal=original_literal)

    @classmethod
    def from_name(cls, name):
        """Build a Color from a CSS color name."""
        self = cls.__new__(cls)  # TODO
        self.original_literal = name

        r, g, b, a = COLOR_NAMES[name]

        self.value = r, g, b, a
        return self

    ### Accessors

    @property
    def rgb(self):
        # TODO: deprecate, relies on internals
        return tuple(self.value[:3])

    @property
    def rgba(self):
        return (
            self.value[0] / 255,
            self.value[1] / 255,
            self.value[2] / 255,
            self.value[3],
        )

    @property
    def hsl(self):
        rgba = self.rgba
        h, l, s = colorsys.rgb_to_hls(*rgba[:3])
        return h, s, l

    @property
    def alpha(self):
        return self.value[3]

    @property
    def rgba255(self):
        return (
            int(self.value[0] * 1 + 0.5),
            int(self.value[1] * 1 + 0.5),
            int(self.value[2] * 1 + 0.5),
            int(self.value[3] * 255 + 0.5),
        )

    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.value))

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if not isinstance(other, Color):
            return Boolean(False)

        # Scale channels to 255 and round to integers; this allows only 8-bit
        # color, but Ruby sass makes the same assumption, and otherwise it's
        # easy to get lots of float errors for HSL colors.
        left = tuple(round(n) for n in self.rgba255)
        right = tuple(round(n) for n in other.rgba255)
        return Boolean(left == right)

    def __add__(self, other):
        if isinstance(other, (Color, Number)):
            return self._operate(other, operator.add)
        else:
            return super(Color, self).__add__(other)

    def __sub__(self, other):
        if isinstance(other, (Color, Number)):
            return self._operate(other, operator.sub)
        else:
            return super(Color, self).__sub__(other)

    def __mul__(self, other):
        if isinstance(other, (Color, Number)):
            return self._operate(other, operator.mul)
        else:
            return super(Color, self).__mul__(other)

    def __div__(self, other):
        if isinstance(other, (Color, Number)):
            return self._operate(other, operator.div)
        else:
            return super(Color, self).__div__(other)

    def _operate(self, other, op):
        if isinstance(other, Number):
            if not other.is_unitless:
                raise ValueError("Expected unitless Number, got %r" % (other,))

            other_rgb = (other.value,) * 3
        elif isinstance(other, Color):
            if self.alpha != other.alpha:
                raise ValueError("Alpha channels must match between %r and %r"
                    % (self, other))

            other_rgb = other.rgb
        else:
            raise TypeError("Expected Color or Number, got %r" % (other,))

        new_rgb = [
            min(255., max(0., op(left, right)))
            # for from_rgb
                / 255.
            for (left, right) in zip(self.rgb, other_rgb)
        ]

        return Color.from_rgb(*new_rgb, alpha=self.alpha)

    def render(self, compress=False):
        """Return a rendered representation of the color.  If `compress` is
        true, the shortest possible representation is used; otherwise, named
        colors are rendered as names and all others are rendered as hex (or
        with the rgba function).
        """

        if not compress and self.original_literal:
            return self.original_literal

        candidates = []

        # TODO this assumes CSS resolution is 8-bit per channel, but so does
        # Ruby.
        r, g, b, a = self.value
        r, g, b = int(round(r)), int(round(g)), int(round(b))

        # Build a candidate list in order of preference.  If `compress` is
        # True, the shortest candidate is used; otherwise, the first candidate
        # is used.

        # Try color name
        key = r, g, b, a
        if key in COLOR_LOOKUP:
            candidates.append(COLOR_LOOKUP[key])

        if a == 1:
            # Hex is always shorter than function notation
            if all(ch % 17 == 0 for ch in (r, g, b)):
                candidates.append("#%1x%1x%1x" % (r // 17, g // 17, b // 17))
            else:
                candidates.append("#%02x%02x%02x" % (r, g, b))
        else:
            # Can't use hex notation for RGBA
            if compress:
                sp = ''
            else:
                sp = ' '
            candidates.append("rgba(%d,%s%d,%s%d,%s%.2g)" % (r, sp, g, sp, b, sp, a))

        if compress:
            return min(candidates, key=len)
        else:
            return candidates[0]


# TODO be unicode-clean and delete this nonsense
DEFAULT_STRING_ENCODING = "utf8"


class String(Value):
    """Represents both CSS quoted string values and CSS identifiers (such as
    `left`).

    Makes no distinction between single and double quotes, except that the same
    quotes are preserved on string literals that pass through unmodified.
    Otherwise, double quotes are used.
    """

    sass_type_name = u'string'

    def __init__(self, value, quotes='"'):
        if isinstance(value, String):
            # TODO unclear if this should be here, but many functions rely on
            # it
            value = value.value
        elif isinstance(value, Number):
            # TODO this may only be necessary in the case of __radd__ and
            # number values
            value = str(value)

        if isinstance(value, six.binary_type):
            value = value.decode(DEFAULT_STRING_ENCODING)

        if not isinstance(value, six.text_type):
            raise TypeError("Expected string, got {0!r}".format(value))

        # TODO probably disallow creating an unquoted string outside a
        # set of chars like [-a-zA-Z0-9]+

        if six.PY3:
            self.value = value
        else:
            # TODO well, at least 3 uses unicode everywhere
            self.value = value.encode(DEFAULT_STRING_ENCODING)
        self.quotes = quotes

    @classmethod
    def unquoted(cls, value):
        """Helper to create a string with no quotes."""
        return cls(value, quotes=None)

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        if self.quotes:
            return self.quotes + escape(self.value) + self.quotes
        else:
            return self.value

    def __repr__(self):
        if self.quotes != '"':
            quotes = ', quotes=%r' % self.quotes
        else:
            quotes = ''
        return '<%s(%s%s)>' % (self.__class__.__name__, repr(self.value), quotes)

    def __eq__(self, other):
        return Boolean(isinstance(other, String) and self.value == other.value)

    def __add__(self, other):
        if isinstance(other, String):
            other_value = other.value
        else:
            other_value = other.render()

        return String(
            self.value + other_value,
            quotes='"' if self.quotes else None)

    def __mul__(self, other):
        # DEVIATION: Ruby Sass doesn't do this, because Ruby doesn't.  But
        # Python does, and in Ruby Sass it's just fatal anyway.
        if not isinstance(other, Number):
            return super(String, self).__mul__(other)

        if not other.is_unitless:
            raise TypeError("Can only multiply strings by unitless numbers")

        n = other.value
        if n != int(n):
            raise ValueError("Can only multiply strings by integers")

        return String(self.value * int(other.value), quotes=self.quotes)

    def render(self, compress=False):
        return self.__str__()


class Map(Value):
    sass_type_name = u'map'

    def __init__(self, pairs, index=None):
        self.pairs = tuple(pairs)

        if index is None:
            self.index = {}
            for key, value in pairs:
                self.index[key] = value
        else:
            self.index = index

    def __repr__(self):
        return "<Map: (%s)>" % (", ".join("%s: %s" % pair for pair in self.pairs),)

    def __hash__(self):
        return hash(self.pairs)

    def __len__(self):
        return len(self.pairs)

    def __iter__(self):
        return iter(self.pairs)

    def __getitem__(self, index):
        return List(self.pairs[index], use_comma=True)

    def __eq__(self, other):
        try:
            return self.pairs == other.to_pairs()
        except ValueError:
            return NotImplemented

    def to_dict(self):
        return self.index

    def to_pairs(self):
        return self.pairs

    def render(self, compress=False):
        raise TypeError("Cannot render map %r as CSS" % (self,))


def expect_type(value, types, unit=any):
    if not isinstance(value, types):
        if isinstance(types, type):
            types = (type,)
        sass_type_names = list(set(t.sass_type_name for t in types))
        sass_type_names.sort()

        # Join with commas in English fashion
        if len(sass_type_names) == 1:
            sass_type = sass_type_names[0]
        elif len(sass_type_names) == 2:
            sass_type = u' or '.join(sass_type_names)
        else:
            sass_type = u', '.join(sass_type_names[:-1])
            sass_type += u', or ' + sass_type_names[-1]

        raise TypeError("Expected %s, got %r" % (sass_type, value))

    if unit is not any and isinstance(value, Number):
        if unit is None and not value.is_unitless:
            raise ValueError("Expected unitless number, got %r" % (value,))

        elif unit == '%' and not (
                value.is_unitless or value.is_simple_unit('%')):
            raise ValueError("Expected unitless number or percentage, got %r" % (value,))
