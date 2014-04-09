from math import pi
import re

# ------------------------------------------------------------------------------
# Built-in CSS color names
# See: http://www.w3.org/TR/css3-color/#svg-color

COLOR_NAMES = {
    'aliceblue': (240, 248, 255, 1),
    'antiquewhite': (250, 235, 215, 1),
    'aqua': (0, 255, 255, 1),
    'aquamarine': (127, 255, 212, 1),
    'azure': (240, 255, 255, 1),
    'beige': (245, 245, 220, 1),
    'bisque': (255, 228, 196, 1),
    'black': (0, 0, 0, 1),
    'blanchedalmond': (255, 235, 205, 1),
    'blue': (0, 0, 255, 1),
    'blueviolet': (138, 43, 226, 1),
    'brown': (165, 42, 42, 1),
    'burlywood': (222, 184, 135, 1),
    'cadetblue': (95, 158, 160, 1),
    'chartreuse': (127, 255, 0, 1),
    'chocolate': (210, 105, 30, 1),
    'coral': (255, 127, 80, 1),
    'cornflowerblue': (100, 149, 237, 1),
    'cornsilk': (255, 248, 220, 1),
    'crimson': (220, 20, 60, 1),
    'cyan': (0, 255, 255, 1),
    'darkblue': (0, 0, 139, 1),
    'darkcyan': (0, 139, 139, 1),
    'darkgoldenrod': (184, 134, 11, 1),
    'darkgray': (169, 169, 169, 1),
    'darkgreen': (0, 100, 0, 1),
    'darkkhaki': (189, 183, 107, 1),
    'darkmagenta': (139, 0, 139, 1),
    'darkolivegreen': (85, 107, 47, 1),
    'darkorange': (255, 140, 0, 1),
    'darkorchid': (153, 50, 204, 1),
    'darkred': (139, 0, 0, 1),
    'darksalmon': (233, 150, 122, 1),
    'darkseagreen': (143, 188, 143, 1),
    'darkslateblue': (72, 61, 139, 1),
    'darkslategray': (47, 79, 79, 1),
    'darkturquoise': (0, 206, 209, 1),
    'darkviolet': (148, 0, 211, 1),
    'deeppink': (255, 20, 147, 1),
    'deepskyblue': (0, 191, 255, 1),
    'dimgray': (105, 105, 105, 1),
    'dodgerblue': (30, 144, 255, 1),
    'firebrick': (178, 34, 34, 1),
    'floralwhite': (255, 250, 240, 1),
    'forestgreen': (34, 139, 34, 1),
    'fuchsia': (255, 0, 255, 1),
    'gainsboro': (220, 220, 220, 1),
    'ghostwhite': (248, 248, 255, 1),
    'gold': (255, 215, 0, 1),
    'goldenrod': (218, 165, 32, 1),
    'gray': (128, 128, 128, 1),
    'green': (0, 128, 0, 1),
    'greenyellow': (173, 255, 47, 1),
    'honeydew': (240, 255, 240, 1),
    'hotpink': (255, 105, 180, 1),
    'indianred': (205, 92, 92, 1),
    'indigo': (75, 0, 130, 1),
    'ivory': (255, 255, 240, 1),
    'khaki': (240, 230, 140, 1),
    'lavender': (230, 230, 250, 1),
    'lavenderblush': (255, 240, 245, 1),
    'lawngreen': (124, 252, 0, 1),
    'lemonchiffon': (255, 250, 205, 1),
    'lightblue': (173, 216, 230, 1),
    'lightcoral': (240, 128, 128, 1),
    'lightcyan': (224, 255, 255, 1),
    'lightgoldenrodyellow': (250, 250, 210, 1),
    'lightgreen': (144, 238, 144, 1),
    'lightgrey': (211, 211, 211, 1),
    'lightpink': (255, 182, 193, 1),
    'lightsalmon': (255, 160, 122, 1),
    'lightseagreen': (32, 178, 170, 1),
    'lightskyblue': (135, 206, 250, 1),
    'lightslategray': (119, 136, 153, 1),
    'lightsteelblue': (176, 196, 222, 1),
    'lightyellow': (255, 255, 224, 1),
    'lime': (0, 255, 0, 1),
    'limegreen': (50, 205, 50, 1),
    'linen': (250, 240, 230, 1),
    'magenta': (255, 0, 255, 1),
    'maroon': (128, 0, 0, 1),
    'mediumaquamarine': (102, 205, 170, 1),
    'mediumblue': (0, 0, 205, 1),
    'mediumorchid': (186, 85, 211, 1),
    'mediumpurple': (147, 112, 219, 1),
    'mediumseagreen': (60, 179, 113, 1),
    'mediumslateblue': (123, 104, 238, 1),
    'mediumspringgreen': (0, 250, 154, 1),
    'mediumturquoise': (72, 209, 204, 1),
    'mediumvioletred': (199, 21, 133, 1),
    'midnightblue': (25, 25, 112, 1),
    'mintcream': (245, 255, 250, 1),
    'mistyrose': (255, 228, 225, 1),
    'moccasin': (255, 228, 181, 1),
    'navajowhite': (255, 222, 173, 1),
    'navy': (0, 0, 128, 1),
    'oldlace': (253, 245, 230, 1),
    'olive': (128, 128, 0, 1),
    'olivedrab': (107, 142, 35, 1),
    'orange': (255, 165, 0, 1),
    'orangered': (255, 69, 0, 1),
    'orchid': (218, 112, 214, 1),
    'palegoldenrod': (238, 232, 170, 1),
    'palegreen': (152, 251, 152, 1),
    'paleturquoise': (175, 238, 238, 1),
    'palevioletred': (219, 112, 147, 1),
    'papayawhip': (255, 239, 213, 1),
    'peachpuff': (255, 218, 185, 1),
    'peru': (205, 133, 63, 1),
    'pink': (255, 192, 203, 1),
    'plum': (221, 160, 221, 1),
    'powderblue': (176, 224, 230, 1),
    'purple': (128, 0, 128, 1),
    'red': (255, 0, 0, 1),
    'rosybrown': (188, 143, 143, 1),
    'royalblue': (65, 105, 225, 1),
    'saddlebrown': (139, 69, 19, 1),
    'salmon': (250, 128, 114, 1),
    'sandybrown': (244, 164, 96, 1),
    'seagreen': (46, 139, 87, 1),
    'seashell': (255, 245, 238, 1),
    'sienna': (160, 82, 45, 1),
    'silver': (192, 192, 192, 1),
    'skyblue': (135, 206, 235, 1),
    'slateblue': (106, 90, 205, 1),
    'slategray': (112, 128, 144, 1),
    'snow': (255, 250, 250, 1),
    'springgreen': (0, 255, 127, 1),
    'steelblue': (70, 130, 180, 1),
    'tan': (210, 180, 140, 1),
    'teal': (0, 128, 128, 1),
    'thistle': (216, 191, 216, 1),
    'tomato': (255, 99, 71, 1),
    'transparent': (0, 0, 0, 0),
    'turquoise': (64, 224, 208, 1),
    'violet': (238, 130, 238, 1),
    'wheat': (245, 222, 179, 1),
    'white': (255, 255, 255, 1),
    'whitesmoke': (245, 245, 245, 1),
    'yellow': (255, 255, 0, 1),
    'yellowgreen': (154, 205, 50, 1),
}
COLOR_LOOKUP = dict((v, k) for (k, v) in COLOR_NAMES.items())

# ------------------------------------------------------------------------------
# Built-in CSS units
# See: http://www.w3.org/TR/2013/CR-css3-values-20130730/#numeric-types

# Maps units to a set of common units per type, with conversion factors
BASE_UNIT_CONVERSIONS = {
    # Lengths
    'mm': (1, 'mm'),
    'cm': (10, 'mm'),
    'in': (25.4, 'mm'),
    'px': (25.4 / 96, 'mm'),
    'pt': (25.4 / 72, 'mm'),
    'pc': (25.4 / 6, 'mm'),

    # Angles
    'deg': (1 / 360, 'turn'),
    'grad': (1 / 400, 'turn'),
    'rad': (pi / 2, 'turn'),
    'turn': (1, 'turn'),

    # Times
    'ms': (1, 'ms'),
    's':  (1000, 'ms'),

    # Frequencies
    'hz': (1, 'hz'),
    'khz': (1000, 'hz'),

    # Resolutions
    'dpi': (1, 'dpi'),
    'dpcm': (2.54, 'dpi'),
    'dppx': (96, 'dpi'),
}


def get_conversion_factor(unit):
    """Look up the "base" unit for this unit and the factor for converting to
    it.

    Returns a 2-tuple of `factor, base_unit`.
    """
    if unit in BASE_UNIT_CONVERSIONS:
        return BASE_UNIT_CONVERSIONS[unit]
    else:
        return 1, unit


def convert_units_to_base_units(units):
    """Convert a set of units into a set of "base" units.

    Returns a 2-tuple of `factor, new_units`.
    """
    total_factor = 1
    new_units = []
    for unit in units:
        if unit not in BASE_UNIT_CONVERSIONS:
            continue

        factor, new_unit = BASE_UNIT_CONVERSIONS[unit]
        total_factor *= factor
        new_units.append(new_unit)

    new_units.sort()
    return total_factor, tuple(new_units)


def count_base_units(units):
    """Returns a dict mapping names of base units to how many times they
    appear in the given iterable of units.  Effectively this counts how
    many length units you have, how many time units, and so forth.
    """
    ret = {}
    for unit in units:
        factor, base_unit = get_conversion_factor(unit)

        ret.setdefault(base_unit, 0)
        ret[base_unit] += 1

    return ret


def cancel_base_units(units, to_remove):
    """Given a list of units, remove a specified number of each base unit.

    Arguments:
        units: an iterable of units
        to_remove: a mapping of base_unit => count, such as that returned from
            count_base_units

    Returns a 2-tuple of (factor, remaining_units).
    """

    # Copy the dict since we're about to mutate it
    to_remove = to_remove.copy()
    remaining_units = []
    total_factor = 1

    for unit in units:
        factor, base_unit = get_conversion_factor(unit)
        if not to_remove.get(base_unit, 0):
            remaining_units.append(unit)
            continue

        total_factor *= factor
        to_remove[base_unit] -= 1

    return total_factor, remaining_units


# A fixed set of units can be omitted when the value is 0
# See: http://www.w3.org/TR/2013/CR-css3-values-20130730/#lengths
ZEROABLE_UNITS = frozenset((
    # Relative lengths
    'em', 'ex', 'ch', 'rem',
    # Viewport
    'vw', 'vh', 'vmin', 'vmax',
    # Absolute lengths
    'cm', 'mm', 'in', 'px', 'pt', 'pc',
))


# ------------------------------------------------------------------------------
# Built-in CSS function reference

# Known function names
BUILTIN_FUNCTIONS = frozenset([
    # CSS2
    'attr', 'counter', 'counters', 'url', 'rgb', 'rect',

    # CSS3 values: http://www.w3.org/TR/css3-values/
    'calc', 'min', 'max', 'cycle',

    # CSS3 colors: http://www.w3.org/TR/css3-color/
    'rgba', 'hsl', 'hsla',

    # CSS3 fonts: http://www.w3.org/TR/css3-fonts/
    'local', 'format',

    # CSS3 images: http://www.w3.org/TR/css3-images/
    'image', 'element',
    'linear-gradient', 'radial-gradient',
    'repeating-linear-gradient', 'repeating-radial-gradient',

    # CSS3 transforms: http://www.w3.org/TR/css3-transforms/
    'perspective',
    'matrix', 'matrix3d',
    'rotate', 'rotateX', 'rotateY', 'rotateZ', 'rotate3d',
    'translate', 'translateX', 'translateY', 'translateZ', 'translate3d',
    'scale', 'scaleX', 'scaleY', 'scaleZ', 'scale3d',
    'skew', 'skewX', 'skewY',

    # CSS3 transitions: http://www.w3.org/TR/css3-transitions/
    'cubic-bezier', 'steps',

    # CSS filter effects:
    # https://dvcs.w3.org/hg/FXTF/raw-file/tip/filters/index.html
    'grayscale', 'sepia', 'saturate', 'hue-rotate', 'invert', 'opacity',
    'brightness', 'contrast', 'blur', 'drop-shadow', 'custom',

    # CSS4 image module:
    # http://dev.w3.org/csswg/css-images/
    'image-set', 'cross-fade',
    'conic-gradient', 'repeating-conic-gradient',

    # Others
    'color-stop',           # Older version of CSS3 gradients
    'mask',                 # ???
    'from', 'to',           # Very old WebKit gradient syntax
])


def is_builtin_css_function(name):
    """Returns whether the given `name` looks like the name of a builtin CSS
    function.

    Unrecognized functions not in this list produce warnings.
    """
    name = name.replace('_', '-')

    if name in BUILTIN_FUNCTIONS:
        return True

    # Vendor-specific functions (-foo-bar) are always okay
    if name[0] == '-' and '-' in name[1:]:
        return True

    return False

# ------------------------------------------------------------------------------
# Bits and pieces of grammar, as regexen

SEPARATOR = '\x00'

_expr_glob_re = re.compile(r'''
    \#\{(.*?)\}                   # Global Interpolation only
''', re.VERBOSE)

# XXX these still need to be fixed; the //-in-functions thing is a chumpy hack
_ml_comment_re = re.compile(r'\/\*(.*?)\*\/', re.DOTALL)
_sl_comment_re = re.compile(r'(?<!\burl[(])(?<!\w{2}:)\/\/.*')

_escape_chars_re = re.compile(r'([^-a-zA-Z0-9_])')
_interpolate_re = re.compile(r'(#\{\s*)?(\$[-\w]+)(?(1)\s*\})')
_spaces_re = re.compile(r'\s+')
_expand_rules_space_re = re.compile(r'\s*{')
_collapse_properties_space_re = re.compile(r'([:#])\s*{')
_variable_re = re.compile('^\\$[-a-zA-Z0-9_]+$')

_strings_re = re.compile(r'([\'"]).*?\1')

_has_placeholder_re = re.compile(r'(?<!\w)([a-z]\w*)?%')
_prop_split_re = re.compile(r'[:=]')
_has_code_re = re.compile('''
    (?:^|(?<=[{;}]))            # the character just before it should be a '{', a ';' or a '}'
    \s*                         # ...followed by any number of spaces
    (?:
        (?:
            \+
        | @include
        | @warn
        | @mixin
        | @function
        | @if
        | @else
        | @for
        | @each
        )
        (?![^(:;}]*['"])
    |
        @import
    )
''', re.VERBOSE)
