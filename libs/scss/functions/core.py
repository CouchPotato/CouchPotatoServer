"""Functions from the Sass "standard library", i.e., built into the original
Ruby implementation.
"""

from __future__ import absolute_import
from __future__ import division

import logging
import math

from six.moves import xrange

from scss.functions.library import FunctionLibrary
from scss.types import Boolean, Color, List, Null, Number, String, Map, expect_type

log = logging.getLogger(__name__)

CORE_LIBRARY = FunctionLibrary()
register = CORE_LIBRARY.register


# ------------------------------------------------------------------------------
# Color creation

def _interpret_percentage(n, relto=1., clamp=True):
    expect_type(n, Number, unit='%')

    if n.is_unitless:
        ret = n.value / relto
    else:
        ret = n.value / 100

    if clamp:
        if ret < 0:
            return 0
        elif ret > 1:
            return 1

    return ret


@register('rgba', 4)
def rgba(r, g, b, a):
    r = _interpret_percentage(r, relto=255)
    g = _interpret_percentage(g, relto=255)
    b = _interpret_percentage(b, relto=255)
    a = _interpret_percentage(a, relto=1)

    return Color.from_rgb(r, g, b, a)


@register('rgb', 3)
def rgb(r, g, b, type='rgb'):
    return rgba(r, g, b, Number(1.0))


@register('rgba', 1)
@register('rgba', 2)
def rgba2(color, a=None):
    if a is None:
        alpha = 1
    else:
        alpha = _interpret_percentage(a)

    return Color.from_rgb(*color.rgba[:3], alpha=alpha)


@register('rgb', 1)
def rgb1(color):
    return rgba2(color, a=Number(1))


@register('hsla', 4)
def hsla(h, s, l, a):
    return Color.from_hsl(
        h.value / 360 % 1,
        # Ruby sass treats plain numbers for saturation and lightness as though
        # they were percentages, just without the %
        _interpret_percentage(s, relto=100),
        _interpret_percentage(l, relto=100),
        alpha=a.value,
    )


@register('hsl', 3)
def hsl(h, s, l):
    return hsla(h, s, l, Number(1))


@register('hsla', 1)
@register('hsla', 2)
def hsla2(color, a=None):
    return rgba2(color, a)


@register('hsl', 1)
def hsl1(color):
    return rgba2(color, a=Number(1))


@register('mix', 2)
@register('mix', 3)
def mix(color1, color2, weight=Number(50, "%")):
    """
    Mixes together two colors. Specifically, takes the average of each of the
    RGB components, optionally weighted by the given percentage.
    The opacity of the colors is also considered when weighting the components.

    Specifically, takes the average of each of the RGB components,
    optionally weighted by the given percentage.
    The opacity of the colors is also considered when weighting the components.

    The weight specifies the amount of the first color that should be included
    in the returned color.
    50%, means that half the first color
        and half the second color should be used.
    25% means that a quarter of the first color
        and three quarters of the second color should be used.

    For example:

        mix(#f00, #00f) => #7f007f
        mix(#f00, #00f, 25%) => #3f00bf
        mix(rgba(255, 0, 0, 0.5), #00f) => rgba(63, 0, 191, 0.75)
    """
    # This algorithm factors in both the user-provided weight
    # and the difference between the alpha values of the two colors
    # to decide how to perform the weighted average of the two RGB values.
    #
    # It works by first normalizing both parameters to be within [-1, 1],
    # where 1 indicates "only use color1", -1 indicates "only use color 0",
    # and all values in between indicated a proportionately weighted average.
    #
    # Once we have the normalized variables w and a,
    # we apply the formula (w + a)/(1 + w*a)
    # to get the combined weight (in [-1, 1]) of color1.
    # This formula has two especially nice properties:
    #
    #   * When either w or a are -1 or 1, the combined weight is also that number
    #     (cases where w * a == -1 are undefined, and handled as a special case).
    #
    #   * When a is 0, the combined weight is w, and vice versa
    #
    # Finally, the weight of color1 is renormalized to be within [0, 1]
    # and the weight of color2 is given by 1 minus the weight of color1.
    #
    # Algorithm from the Sass project: http://sass-lang.com/

    p = _interpret_percentage(weight)

    # Scale weight to [-1, 1]
    w = p * 2 - 1
    # Compute difference in alpha channels
    a = color1.alpha - color2.alpha

    # Weight of first color
    if w * a == -1:
        # Avoid zero-div case
        scaled_weight1 = w
    else:
        scaled_weight1 = (w + a) / (1 + w * a)

    # Unscale back to [0, 1] and get the weight of the other color
    w1 = (scaled_weight1 + 1) / 2
    w2 = 1 - w1

    # Do the scaling.  Note that alpha isn't scaled by alpha, as that wouldn't
    # make much sense; it uses the original untwiddled weight, p.
    channels = [
        ch1 * w1 + ch2 * w2
        for (ch1, ch2) in zip(color1.rgba[:3], color2.rgba[:3])]
    alpha = color1.alpha * p + color2.alpha * (1 - p)
    return Color.from_rgb(*channels, alpha=alpha)


# ------------------------------------------------------------------------------
# Color inspection

@register('red', 1)
def red(color):
    r, g, b, a = color.rgba
    return Number(r * 255)


@register('green', 1)
def green(color):
    r, g, b, a = color.rgba
    return Number(g * 255)


@register('blue', 1)
def blue(color):
    r, g, b, a = color.rgba
    return Number(b * 255)


@register('opacity', 1)
@register('alpha', 1)
def alpha(color):
    return Number(color.alpha)


@register('hue', 1)
def hue(color):
    h, s, l = color.hsl
    return Number(h * 360, "deg")


@register('saturation', 1)
def saturation(color):
    h, s, l = color.hsl
    return Number(s * 100, "%")


@register('lightness', 1)
def lightness(color):
    h, s, l = color.hsl
    return Number(l * 100, "%")


@register('ie-hex-str', 1)
def ie_hex_str(color):
    c = Color(color).value
    return String(u'#%02X%02X%02X%02X' % (round(c[3] * 255), round(c[0]), round(c[1]), round(c[2])))


# ------------------------------------------------------------------------------
# Color modification

@register('fade-in', 2)
@register('fadein', 2)
@register('opacify', 2)
def opacify(color, amount):
    r, g, b, a = color.rgba
    return Color.from_rgb(
        r, g, b,
        alpha=color.alpha + amount.value)


@register('fade-out', 2)
@register('fadeout', 2)
@register('transparentize', 2)
def transparentize(color, amount):
    r, g, b, a = color.rgba
    return Color.from_rgb(
        r, g, b,
        alpha=color.alpha - amount.value)


@register('lighten', 2)
def lighten(color, amount):
    return adjust_color(color, lightness=amount)


@register('darken', 2)
def darken(color, amount):
    return adjust_color(color, lightness=-amount)


@register('saturate', 2)
def saturate(color, amount):
    return adjust_color(color, saturation=amount)


@register('desaturate', 2)
def desaturate(color, amount):
    return adjust_color(color, saturation=-amount)


@register('greyscale', 1)
def greyscale(color):
    h, s, l = color.hsl
    return Color.from_hsl(h, 0, l, alpha=color.alpha)


@register('grayscale', 1)
def grayscale(color):
    if isinstance(color, Number) and color.is_unitless:
        # grayscale(n) is a CSS3 filter and should be left intact, but only
        # when using the "a" spelling
        return String.unquoted("grayscale(%d)" % (color.value,))
    else:
        return greyscale(color)


@register('spin', 2)
@register('adjust-hue', 2)
def adjust_hue(color, degrees):
    h, s, l = color.hsl
    delta = degrees.value / 360
    return Color.from_hsl((h + delta) % 1, s, l, alpha=color.alpha)


@register('complement', 1)
def complement(color):
    h, s, l = color.hsl
    return Color.from_hsl((h + 0.5) % 1, s, l, alpha=color.alpha)


@register('invert', 1)
def invert(color):
    """
    Returns the inverse (negative) of a color.
    The red, green, and blue values are inverted, while the opacity is left alone.
    """
    r, g, b, a = color.rgba
    return Color.from_rgb(1 - r, 1 - g, 1 - b, alpha=a)


@register('adjust-lightness', 2)
def adjust_lightness(color, amount):
    return adjust_color(color, lightness=amount)


@register('adjust-saturation', 2)
def adjust_saturation(color, amount):
    return adjust_color(color, saturation=amount)


@register('scale-lightness', 2)
def scale_lightness(color, amount):
    return scale_color(color, lightness=amount)


@register('scale-saturation', 2)
def scale_saturation(color, amount):
    return scale_color(color, saturation=amount)


@register('adjust-color')
def adjust_color(color, red=None, green=None, blue=None, hue=None, saturation=None, lightness=None, alpha=None):
    do_rgb = red or green or blue
    do_hsl = hue or saturation or lightness
    if do_rgb and do_hsl:
        raise ValueError("Can't adjust both RGB and HSL channels at the same time")

    zero = Number(0)
    a = color.alpha + (alpha or zero).value

    if do_rgb:
        r, g, b = color.rgba[:3]
        channels = [
            current + (adjustment or zero).value / 255
            for (current, adjustment) in zip(color.rgba, (red, green, blue))]
        return Color.from_rgb(*channels, alpha=a)

    else:
        h, s, l = color.hsl
        h = (h + (hue or zero).value / 360) % 1
        s += _interpret_percentage(saturation or zero, relto=100, clamp=False)
        l += _interpret_percentage(lightness or zero, relto=100, clamp=False)
        return Color.from_hsl(h, s, l, a)


def _scale_channel(channel, scaleby):
    if scaleby is None:
        return channel

    expect_type(scaleby, Number)
    if not scaleby.is_simple_unit('%'):
        raise ValueError("Expected percentage, got %r" % (scaleby,))

    factor = scaleby.value / 100
    if factor > 0:
        # Add x% of the remaining range, up to 1
        return channel + (1 - channel) * factor
    else:
        # Subtract x% of the existing channel.  We add here because the factor
        # is already negative
        return channel * (1 + factor)


@register('scale-color')
def scale_color(color, red=None, green=None, blue=None, saturation=None, lightness=None, alpha=None):
    do_rgb = red or green or blue
    do_hsl = saturation or lightness
    if do_rgb and do_hsl:
        raise ValueError("Can't scale both RGB and HSL channels at the same time")

    scaled_alpha = _scale_channel(color.alpha, alpha)

    if do_rgb:
        channels = [
            _scale_channel(channel, scaleby)
            for channel, scaleby in zip(color.rgba, (red, green, blue))]
        return Color.from_rgb(*channels, alpha=scaled_alpha)

    else:
        channels = [
            _scale_channel(channel, scaleby)
            for channel, scaleby in zip(color.hsl, (None, saturation, lightness))]
        return Color.from_hsl(*channels, alpha=scaled_alpha)


@register('change-color')
def change_color(color, red=None, green=None, blue=None, hue=None, saturation=None, lightness=None, alpha=None):
    do_rgb = red or green or blue
    do_hsl = hue or saturation or lightness
    if do_rgb and do_hsl:
        raise ValueError("Can't change both RGB and HSL channels at the same time")

    if alpha is None:
        alpha = color.alpha
    else:
        alpha = alpha.value

    if do_rgb:
        channels = list(color.rgba[:3])
        if red:
            channels[0] = _interpret_percentage(red, relto=255)
        if green:
            channels[1] = _interpret_percentage(green, relto=255)
        if blue:
            channels[2] = _interpret_percentage(blue, relto=255)

        return Color.from_rgb(*channels, alpha=alpha)

    else:
        channels = list(color.hsl)
        if hue:
            expect_type(hue, Number, unit=None)
            channels[0] = (hue.value / 360) % 1
        # Ruby sass treats plain numbers for saturation and lightness as though
        # they were percentages, just without the %
        if saturation:
            channels[1] = _interpret_percentage(saturation, relto=100)
        if lightness:
            channels[2] = _interpret_percentage(lightness, relto=100)

        return Color.from_hsl(*channels, alpha=alpha)


# ------------------------------------------------------------------------------
# String functions

@register('e', 1)
@register('escape', 1)
@register('unquote')
def unquote(*args):
    arg = List.from_maybe_starargs(args).maybe()

    if isinstance(arg, String):
        return String(arg.value, quotes=None)
    else:
        return String(arg.render(), quotes=None)


@register('quote')
def quote(*args):
    arg = List.from_maybe_starargs(args).maybe()

    if isinstance(arg, String):
        return String(arg.value, quotes='"')
    else:
        return String(arg.render(), quotes='"')


@register('str-length', 1)
def str_length(string):
    expect_type(string, String)

    # nb: can't use `len(string)`, because that gives the Sass list length,
    # which is 1
    return Number(len(string.value))


# TODO this and several others should probably also require integers
# TODO and assert that the indexes are valid
@register('str-insert', 3)
def str_insert(string, insert, index):
    expect_type(string, String)
    expect_type(insert, String)
    expect_type(index, Number, unit=None)

    py_index = index.to_python_index(len(string.value), check_bounds=False)
    return String(
        string.value[:py_index] +
            insert.value +
            string.value[py_index:],
        quotes=string.quotes)


@register('str-index', 2)
def str_index(string, substring):
    expect_type(string, String)
    expect_type(substring, String)

    # 1-based indexing, with 0 for failure
    return Number(string.value.find(substring.value) + 1)


@register('str-slice', 2)
@register('str-slice', 3)
def str_slice(string, start_at, end_at=None):
    expect_type(string, String)
    expect_type(start_at, Number, unit=None)
    py_start_at = start_at.to_python_index(len(string.value))

    if end_at is None:
        py_end_at = None
    else:
        expect_type(end_at, Number, unit=None)
        # Endpoint is inclusive, unlike Python
        py_end_at = end_at.to_python_index(len(string.value)) + 1

    return String(
        string.value[py_start_at:py_end_at],
        quotes=string.quotes)


@register('to-upper-case', 1)
def to_upper_case(string):
    expect_type(string, String)

    return String(string.value.upper(), quotes=string.quotes)


@register('to-lower-case', 1)
def to_lower_case(string):
    expect_type(string, String)

    return String(string.value.lower(), quotes=string.quotes)


# ------------------------------------------------------------------------------
# Number functions

@register('percentage', 1)
def percentage(value):
    expect_type(value, Number, unit=None)
    return value * Number(100, unit='%')

CORE_LIBRARY.add(Number.wrap_python_function(abs), 'abs', 1)
CORE_LIBRARY.add(Number.wrap_python_function(round), 'round', 1)
CORE_LIBRARY.add(Number.wrap_python_function(math.ceil), 'ceil', 1)
CORE_LIBRARY.add(Number.wrap_python_function(math.floor), 'floor', 1)


# ------------------------------------------------------------------------------
# List functions

def __parse_separator(separator, default_from=None):
    if separator is None:
        separator = 'auto'
    separator = String.unquoted(separator).value

    if separator == 'comma':
        return True
    elif separator == 'space':
        return False
    elif separator == 'auto':
        if not default_from:
            return True
        elif len(default_from) < 2:
            return True
        else:
            return default_from.use_comma
    else:
        raise ValueError('Separator must be auto, comma, or space')


# TODO get the compass bit outta here
@register('-compass-list-size')
@register('length')
def _length(*lst):
    if len(lst) == 1 and isinstance(lst[0], (list, tuple, List)):
        lst = lst[0]
    return Number(len(lst))


@register('set-nth', 3)
def set_nth(list, n, value):
    expect_type(n, Number, unit=None)

    py_n = n.to_python_index(len(list))
    return List(
        tuple(list[:py_n]) + (value,) + tuple(list[py_n + 1:]),
        use_comma=list.use_comma)


# TODO get the compass bit outta here
@register('-compass-nth', 2)
@register('nth', 2)
def nth(lst, n):
    """Return the nth item in the list."""
    expect_type(n, (String, Number), unit=None)

    if isinstance(n, String):
        if n.value.lower() == 'first':
            i = 0
        elif n.value.lower() == 'last':
            i = -1
        else:
            raise ValueError("Invalid index %r" % (n,))
    else:
        # DEVIATION: nth treats lists as circular lists
        i = n.to_python_index(len(lst), circular=True)

    return lst[i]


@register('join', 2)
@register('join', 3)
def join(lst1, lst2, separator=None):
    ret = []
    ret.extend(List.from_maybe(lst1))
    ret.extend(List.from_maybe(lst2))

    use_comma = __parse_separator(separator, default_from=lst1)
    return List(ret, use_comma=use_comma)


@register('min')
def min_(*lst):
    if len(lst) == 1 and isinstance(lst[0], (list, tuple, List)):
        lst = lst[0]
    return min(lst)


@register('max')
def max_(*lst):
    if len(lst) == 1 and isinstance(lst[0], (list, tuple, List)):
        lst = lst[0]
    return max(lst)


@register('append', 2)
@register('append', 3)
def append(lst, val, separator=None):
    ret = []
    ret.extend(List.from_maybe(lst))
    ret.append(val)

    use_comma = __parse_separator(separator, default_from=lst)
    return List(ret, use_comma=use_comma)


@register('index', 2)
def index(lst, val):
    for i in xrange(len(lst)):
        if lst.value[i] == val:
            return Number(i + 1)
    return Boolean(False)


@register('zip')
def zip_(*lists):
    return List(
        [List(zipped) for zipped in zip(*lists)],
        use_comma=True)


# TODO need a way to use "list" as the arg name without shadowing the builtin
@register('list-separator', 1)
def list_separator(list):
    if list.use_comma:
        return String.unquoted('comma')
    else:
        return String.unquoted('space')


# ------------------------------------------------------------------------------
# Map functions

@register('map-get', 2)
def map_get(map, key):
    return map.to_dict().get(key, Null())


@register('map-merge', 2)
def map_merge(*maps):
    key_order = []
    index = {}
    for map in maps:
        for key, value in map.to_pairs():
            if key not in index:
                key_order.append(key)

            index[key] = value

    pairs = [(key, index[key]) for key in key_order]
    return Map(pairs, index=index)


@register('map-keys', 1)
def map_keys(map):
    return List(
        [k for (k, v) in map.to_pairs()],
        use_comma=True)


@register('map-values', 1)
def map_values(map):
    return List(
        [v for (k, v) in map.to_pairs()],
        use_comma=True)


@register('map-has-key', 2)
def map_has_key(map, key):
    return Boolean(key in map.to_dict())


# DEVIATIONS: these do not exist in ruby sass

@register('map-get', 3)
def map_get3(map, key, default):
    return map.to_dict().get(key, default)


@register('map-get-nested', 2)
@register('map-get-nested', 3)
def map_get_nested3(map, keys, default=Null()):
    for key in keys:
        map = map.to_dict().get(key, None)
        if map is None:
            return default

    return map


@register('map-merge-deep', 2)
def map_merge_deep(*maps):
    pairs = []
    keys = set()
    for map in maps:
        for key, value in map.to_pairs():
            keys.add(key)

    for key in keys:
        values = [map.to_dict().get(key, None) for map in maps]
        values = [v for v in values if v is not None]
        if all(isinstance(v, Map) for v in values):
            pairs.append((key, map_merge_deep(*values)))
        else:
            pairs.append((key, values[-1]))

    return Map(pairs)


# ------------------------------------------------------------------------------
# Meta functions

@register('type-of', 1)
def _type_of(obj):  # -> bool, number, string, color, list
    return String(obj.sass_type_name)


@register('unit', 1)
def unit(number):  # -> px, em, cm, etc.
    numer = '*'.join(sorted(number.unit_numer))
    denom = '*'.join(sorted(number.unit_denom))

    if denom:
        ret = numer + '/' + denom
    else:
        ret = numer
    return String.unquoted(ret)


@register('unitless', 1)
def unitless(value):
    if not isinstance(value, Number):
        raise TypeError("Expected number, got %r" % (value,))

    return Boolean(value.is_unitless)


@register('comparable', 2)
def comparable(number1, number2):
    left = number1.to_base_units()
    right = number2.to_base_units()
    return Boolean(
        left.unit_numer == right.unit_numer
        and left.unit_denom == right.unit_denom)


# ------------------------------------------------------------------------------
# Miscellaneous

@register('if', 2)
@register('if', 3)
def if_(condition, if_true, if_false=Null()):
    return if_true if condition else if_false
