"""Utilities for working with gradients.  Inspired by Compass, but not quite
the same.
"""

from __future__ import absolute_import

import base64
import logging

import six

from scss.functions.library import FunctionLibrary
from scss.functions.compass.helpers import opposite_position, position
from scss.types import Color, List, Number, String
from scss.util import escape, split_params, to_float, to_str

log = logging.getLogger(__name__)

COMPASS_GRADIENTS_LIBRARY = FunctionLibrary()
register = COMPASS_GRADIENTS_LIBRARY.register


# ------------------------------------------------------------------------------

def __color_stops(percentages, *args):
    if len(args) == 1:
        if isinstance(args[0], (list, tuple, List)):
            list(args[0])
        elif isinstance(args[0], (String, six.string_types)):
            color_stops = []
            colors = split_params(getattr(args[0], 'value', args[0]))
            for color in colors:
                color = color.strip()
                if color.startswith('color-stop('):
                    s, c = split_params(color[11:].rstrip(')'))
                    s = s.strip()
                    c = c.strip()
                else:
                    c, s = color.split()
                color_stops.append((to_float(s), c))
            return color_stops

    colors = []
    stops = []
    prev_color = False
    for c in args:
        for c in List.from_maybe(c):
            if isinstance(c, Color):
                if prev_color:
                    stops.append(None)
                colors.append(c)
                prev_color = True
            elif isinstance(c, Number):
                stops.append(c)
                prev_color = False

    if prev_color:
        stops.append(None)
    stops = stops[:len(colors)]
    if stops[0] is None:
        stops[0] = Number(0, '%')
    if stops[-1] is None:
        stops[-1] = Number(100, '%')

    maxable_stops = [s for s in stops if s and not s.is_simple_unit('%')]
    if maxable_stops:
        max_stops = max(maxable_stops)
    else:
        max_stops = None

    stops = [_s / max_stops if _s and not _s.is_simple_unit('%') else _s for _s in stops]

    init = 0
    start = None
    for i, s in enumerate(stops + [1.0]):
        if s is None:
            if start is None:
                start = i
            end = i
        else:
            final = s
            if start is not None:
                stride = (final - init) / Number(end - start + 1 + (1 if i < len(stops) else 0))
                for j in range(start, end + 1):
                    stops[j] = init + stride * Number(j - start + 1)
            init = final
            start = None

    if not max_stops or percentages:
        pass
    else:
        stops = [s if s.is_simple_unit('%') else s * max_stops for s in stops]

    return list(zip(stops, colors))


def _render_standard_color_stops(color_stops):
    pairs = []
    for i, (stop, color) in enumerate(color_stops):
        if ((i == 0 and stop == Number(0, '%')) or
                (i == len(color_stops) - 1 and stop == Number(100, '%'))):
            pairs.append(color)
        else:
            pairs.append(List([color, stop], use_comma=False))

    return List(pairs, use_comma=True)


@register('grad-color-stops')
def grad_color_stops(*args):
    args = List.from_maybe_starargs(args)
    color_stops = __color_stops(True, *args)
    ret = ', '.join(['color-stop(%s, %s)' % (s.render(), c.render()) for s, c in color_stops])
    return String.unquoted(ret)


def __grad_end_position(radial, color_stops):
    return __grad_position(-1, 100, radial, color_stops)


@register('grad-point')
def grad_point(*p):
    pos = set()
    hrz = vrt = Number(0.5, '%')
    for _p in p:
        pos.update(String.unquoted(_p).value.split())
    if 'left' in pos:
        hrz = Number(0, '%')
    elif 'right' in pos:
        hrz = Number(1, '%')
    if 'top' in pos:
        vrt = Number(0, '%')
    elif 'bottom' in pos:
        vrt = Number(1, '%')
    return List([v for v in (hrz, vrt) if v is not None])


def __grad_position(index, default, radial, color_stops):
    try:
        stops = Number(color_stops[index][0])
        if radial and not stops.is_simple_unit('px') and (index == 0 or index == -1 or index == len(color_stops) - 1):
            log.warn("Webkit only supports pixels for the start and end stops for radial gradients. Got %s", stops)
    except IndexError:
        stops = Number(default)
    return stops


@register('grad-end-position')
def grad_end_position(*color_stops):
    color_stops = __color_stops(False, *color_stops)
    return Number(__grad_end_position(False, color_stops))


@register('color-stops')
def color_stops(*args):
    args = List.from_maybe_starargs(args)
    color_stops = __color_stops(False, *args)
    ret = ', '.join(['%s %s' % (c.render(), s.render()) for s, c in color_stops])
    return String.unquoted(ret)


@register('color-stops-in-percentages')
def color_stops_in_percentages(*args):
    args = List.from_maybe_starargs(args)
    color_stops = __color_stops(True, *args)
    ret = ', '.join(['%s %s' % (c.render(), s.render()) for s, c in color_stops])
    return String.unquoted(ret)


def _get_gradient_position_and_angle(args):
    for arg in args:
        ret = None
        skip = False
        for a in arg:
            if isinstance(a, Color):
                skip = True
                break
            elif isinstance(a, Number):
                ret = arg
        if skip:
            continue
        if ret is not None:
            return ret
        for seek in (
            'center',
            'top', 'bottom',
            'left', 'right',
        ):
            if String(seek) in arg:
                return arg
    return None


def _get_gradient_shape_and_size(args):
    for arg in args:
        for seek in (
            'circle', 'ellipse',
            'closest-side', 'closest-corner',
            'farthest-side', 'farthest-corner',
            'contain', 'cover',
        ):
            if String(seek) in arg:
                return arg
    return None


def _get_gradient_color_stops(args):
    color_stops = []
    for arg in args:
        for a in List.from_maybe(arg):
            if isinstance(a, Color):
                color_stops.append(arg)
                break
    return color_stops or None


@register('radial-gradient')
def radial_gradient(*args):
    args = List.from_maybe_starargs(args)

    position_and_angle = _get_gradient_position_and_angle(args)
    shape_and_size = _get_gradient_shape_and_size(args)
    color_stops = _get_gradient_color_stops(args)
    if color_stops is None:
        raise Exception('No color stops provided to radial-gradient function')
    color_stops = __color_stops(False, *color_stops)

    args = [
        position(position_and_angle) if position_and_angle is not None else None,
        shape_and_size if shape_and_size is not None else None,
    ]
    args.extend(_render_standard_color_stops(color_stops))

    to__s = 'radial-gradient(' + ', '.join(to_str(a) for a in args or [] if a is not None) + ')'
    ret = String.unquoted(to__s)

    def to__css2():
        return String.unquoted('')
    ret.to__css2 = to__css2

    def to__moz():
        return String.unquoted('-moz-' + to__s)
    ret.to__moz = to__moz

    def to__pie():
        log.warn("PIE does not support radial-gradient.")
        return String.unquoted('-pie-radial-gradient(unsupported)')
    ret.to__pie = to__pie

    def to__webkit():
        return String.unquoted('-webkit-' + to__s)
    ret.to__webkit = to__webkit

    def to__owg():
        args = [
            'radial',
            grad_point(position_and_angle) if position_and_angle is not None else 'center',
            '0',
            grad_point(position_and_angle) if position_and_angle is not None else 'center',
            __grad_end_position(True, color_stops),
        ]
        args.extend('color-stop(%s, %s)' % (s.render(), c.render()) for s, c in color_stops)
        ret = '-webkit-gradient(' + ', '.join(to_str(a) for a in args or [] if a is not None) + ')'
        return String.unquoted(ret)
    ret.to__owg = to__owg

    def to__svg():
        return radial_svg_gradient(color_stops, position_and_angle or 'center')
    ret.to__svg = to__svg

    return ret


@register('linear-gradient')
def linear_gradient(*args):
    args = List.from_maybe_starargs(args)

    position_and_angle = _get_gradient_position_and_angle(args)
    color_stops = _get_gradient_color_stops(args)
    if color_stops is None:
        raise Exception('No color stops provided to linear-gradient function')
    color_stops = __color_stops(False, *color_stops)

    args = [
        position(position_and_angle) if position_and_angle is not None else None,
    ]
    args.extend(_render_standard_color_stops(color_stops))

    to__s = 'linear-gradient(' + ', '.join(to_str(a) for a in args or [] if a is not None) + ')'
    ret = String.unquoted(to__s)

    def to__css2():
        return String.unquoted('')
    ret.to__css2 = to__css2

    def to__moz():
        return String.unquoted('-moz-' + to__s)
    ret.to__moz = to__moz

    def to__pie():
        return String.unquoted('-pie-' + to__s)
    ret.to__pie = to__pie

    def to__ms():
        return String.unquoted('-ms-' + to__s)
    ret.to__ms = to__ms

    def to__o():
        return String.unquoted('-o-' + to__s)
    ret.to__o = to__o

    def to__webkit():
        return String.unquoted('-webkit-' + to__s)
    ret.to__webkit = to__webkit

    def to__owg():
        args = [
            'linear',
            position(position_and_angle or None),
            opposite_position(position_and_angle or None),
        ]
        args.extend('color-stop(%s, %s)' % (s.render(), c.render()) for s, c in color_stops)
        ret = '-webkit-gradient(' + ', '.join(to_str(a) for a in args if a is not None) + ')'
        return String.unquoted(ret)
    ret.to__owg = to__owg

    def to__svg():
        return linear_svg_gradient(color_stops, position_and_angle or 'top')
    ret.to__svg = to__svg

    return ret


@register('radial-svg-gradient')
def radial_svg_gradient(*args):
    args = List.from_maybe_starargs(args)
    color_stops = args
    center = None
    if isinstance(args[-1], (String, Number, six.string_types)):
        center = args[-1]
        color_stops = args[:-1]
    color_stops = __color_stops(False, *color_stops)
    cx, cy = zip(*grad_point(center).items())[1]
    r = __grad_end_position(True, color_stops)
    svg = __radial_svg(color_stops, cx, cy, r)
    url = 'data:' + 'image/svg+xml' + ';base64,' + base64.b64encode(svg)
    inline = 'url("%s")' % escape(url)
    return String.unquoted(inline)


@register('linear-svg-gradient')
def linear_svg_gradient(*args):
    args = List.from_maybe_starargs(args)
    color_stops = args
    start = None
    if isinstance(args[-1], (String, Number, six.string_types)):
        start = args[-1]
        color_stops = args[:-1]
    color_stops = __color_stops(False, *color_stops)
    x1, y1 = zip(*grad_point(start).items())[1]
    x2, y2 = zip(*grad_point(opposite_position(start)).items())[1]
    svg = _linear_svg(color_stops, x1, y1, x2, y2)
    url = 'data:' + 'image/svg+xml' + ';base64,' + base64.b64encode(svg)
    inline = 'url("%s")' % escape(url)
    return String.unquoted(inline)


def __color_stops_svg(color_stops):
    ret = ''.join('<stop offset="%s" stop-color="%s"/>' % (to_str(s), c) for s, c in color_stops)
    return ret


def __svg_template(gradient):
    ret = '<?xml version="1.0" encoding="utf-8"?>\
<svg version="1.1" xmlns="http://www.w3.org/2000/svg">\
<defs>%s</defs>\
<rect x="0" y="0" width="100%%" height="100%%" fill="url(#grad)" />\
</svg>' % gradient
    return ret


def _linear_svg(color_stops, x1, y1, x2, y2):
    gradient = '<linearGradient id="grad" x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>' % (
        to_str(Number(x1)),
        to_str(Number(y1)),
        to_str(Number(x2)),
        to_str(Number(y2)),
        __color_stops_svg(color_stops)
    )
    return __svg_template(gradient)


def __radial_svg(color_stops, cx, cy, r):
    gradient = '<radialGradient id="grad" gradientUnits="userSpaceOnUse" cx="%s" cy="%s" r="%s">%s</radialGradient>' % (
        to_str(Number(cx)),
        to_str(Number(cy)),
        to_str(Number(r)),
        __color_stops_svg(color_stops)
    )
    return __svg_template(gradient)
