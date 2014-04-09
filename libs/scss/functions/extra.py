"""Functions new to the pyScss library."""

from __future__ import absolute_import

import base64
import hashlib
import logging
import os.path
import random

import six
from six.moves import xrange

from scss import config
from scss.functions.library import FunctionLibrary
from scss.types import Color, Number, String, List
from scss.util import escape

try:
    from PIL import Image, ImageDraw
except ImportError:
    try:
        import Image
        import ImageDraw
    except:
        Image = None

log = logging.getLogger(__name__)

EXTRA_LIBRARY = FunctionLibrary()
register = EXTRA_LIBRARY.register


# ------------------------------------------------------------------------------
# Image stuff
def _image_noise(pixdata, size, density=None, intensity=None, color=None, opacity=None, monochrome=None, background=None):
    if not density:
        density = [0.8]
    elif not isinstance(density, (tuple, list)):
        density = [density]

    if not intensity:
        intensity = [0.5]
    elif not isinstance(intensity, (tuple, list)):
        intensity = [intensity]

    if not color:
        color = [(0, 0, 0, 0)]
    elif not isinstance(color, (tuple, list)) or not isinstance(color[0], (tuple, list)):
        color = [color]

    if not opacity:
        opacity = [0.2]
    elif not isinstance(opacity, (tuple, list)):
        opacity = [opacity]

    if not monochrome:
        monochrome = [False]
    elif not isinstance(monochrome, (tuple, list)):
        monochrome = [monochrome]

    pixels = {}

    if background:
        for y in xrange(size):
            for x in xrange(size):
                ca = float(background[3])
                pixels[(x, y)] = (background[0] * ca, background[1] * ca, background[2] * ca, ca)

    loops = max(map(len, (density, intensity, color, opacity, monochrome)))
    for l in range(loops):
        _density = density[l % len(density)]
        _intensity = intensity[l % len(intensity)]
        _color = color[l % len(color)]
        _opacity = opacity[l % len(opacity)]
        _monochrome = monochrome[l % len(monochrome)]
        _intensity = 1 - _intensity
        if _intensity < 0.5:
            cx = 255 * _intensity
            cm = cx
        else:
            cx = 255 * (1 - _intensity)
            cm = 255 * _intensity
        xa = int(cm - cx)
        xb = int(cm + cx)
        if xa > 0:
            xa &= 255
        else:
            xa = 0
        if xb > 0:
            xb &= 255
        else:
            xb = 0
        r, g, b, a = _color
        for i in xrange(int(round(_density * size ** 2))):
            x = random.randint(1, size)
            y = random.randint(1, size)
            cc = random.randint(xa, xb)
            cr = (cc) * (1 - a) + a * r
            cg = (cc if _monochrome else random.randint(xa, xb)) * (1 - a) + a * g
            cb = (cc if _monochrome else random.randint(xa, xb)) * (1 - a) + a * b
            ca = random.random() * _opacity
            ica = 1 - ca
            pos = (x - 1, y - 1)
            dst = pixels.get(pos, (0, 0, 0, 0))
            src = (cr * ca, cg * ca, cb * ca, ca)
            pixels[pos] = (src[0] + dst[0] * ica, src[1] + dst[1] * ica, src[2] + dst[2] * ica, src[3] + dst[3] * ica)

    for pos, col in pixels.items():
        ca = col[3]
        if ca:
            pixdata[pos] = tuple(int(round(c)) for c in (col[0] / ca, col[1] / ca, col[2] / ca, ca * 255))


def _image_brushed(pixdata, size, density=None, intensity=None, color=None, opacity=None, monochrome=None, direction=None, spread=None, background=None):
    if not density:
        density = [0.8]
    elif not isinstance(density, (tuple, list)):
        density = [density]

    if not intensity:
        intensity = [0.5]
    elif not isinstance(intensity, (tuple, list)):
        intensity = [intensity]

    if not color:
        color = [(0, 0, 0, 0)]
    elif not isinstance(color, (tuple, list)) or not isinstance(color[0], (tuple, list)):
        color = [color]

    if not opacity:
        opacity = [0.2]
    elif not isinstance(opacity, (tuple, list)):
        opacity = [opacity]

    if not monochrome:
        monochrome = [False]
    elif not isinstance(monochrome, (tuple, list)):
        monochrome = [monochrome]

    if not direction:
        direction = [0]
    elif not isinstance(direction, (tuple, list)):
        direction = [direction]

    if not spread:
        spread = [0]
    elif not isinstance(spread, (tuple, list)):
        spread = [spread]

    def ppgen(d):
        if d is None:
            return
        d = d % 4
        if d == 0:
            pp = lambda x, y, o: ((x - o) % size, y)
        elif d == 1:
            pp = lambda x, y, o: ((x - o) % size, (y + x - o) % size)
        elif d == 2:
            pp = lambda x, y, o: (y, (x - o) % size)
        else:
            pp = lambda x, y, o: ((x - o) % size, (y - x - o) % size)
        return pp

    pixels = {}

    if background:
        for y in xrange(size):
            for x in xrange(size):
                ca = float(background[3])
                pixels[(x, y)] = (background[0] * ca, background[1] * ca, background[2] * ca, ca)

    loops = max(map(len, (density, intensity, color, opacity, monochrome, direction, spread)))
    for l in range(loops):
        _density = density[l % len(density)]
        _intensity = intensity[l % len(intensity)]
        _color = color[l % len(color)]
        _opacity = opacity[l % len(opacity)]
        _monochrome = monochrome[l % len(monochrome)]
        _direction = direction[l % len(direction)]
        _spread = spread[l % len(spread)]
        _intensity = 1 - _intensity
        if _intensity < 0.5:
            cx = 255 * _intensity
            cm = cx
        else:
            cx = 255 * (1 - _intensity)
            cm = 255 * _intensity
        xa = int(cm - cx)
        xb = int(cm + cx)
        if xa > 0:
            xa &= 255
        else:
            xa = 0
        if xb > 0:
            xb &= 255
        else:
            xb = 0
        r, g, b, a = _color
        pp = ppgen(_direction)
        if pp:
            for y in xrange(size):
                if _spread and (y + (l % 2)) % _spread:
                    continue
                o = random.randint(1, size)
                cc = random.randint(xa, xb)
                cr = (cc) * (1 - a) + a * r
                cg = (cc if _monochrome else random.randint(xa, xb)) * (1 - a) + a * g
                cb = (cc if _monochrome else random.randint(xa, xb)) * (1 - a) + a * b
                da = random.randint(0, 255) * _opacity
                ip = round((size / 2.0 * _density) / int(1 / _density))
                iq = round((size / 2.0 * (1 - _density)) / int(1 / _density))
                if ip:
                    i = da / ip
                    aa = 0
                else:
                    i = 0
                    aa = da
                d = 0
                p = ip
                for x in xrange(size):
                    if d == 0:
                        if p > 0:
                            p -= 1
                            aa += i
                        else:
                            d = 1
                            q = iq
                    elif d == 1:
                        if q > 0:
                            q -= 1
                        else:
                            d = 2
                            p = ip
                    elif d == 2:
                        if p > 0:
                            p -= 1
                            aa -= i
                        else:
                            d = 3
                            q = iq
                    elif d == 3:
                        if q > 0:
                            q -= 1
                        else:
                            d = 0
                            p = ip
                    if aa > 0:
                        ca = aa / 255.0
                    else:
                        ca = 0.0
                    ica = 1 - ca
                    pos = pp(x, y, o)
                    dst = pixels.get(pos, (0, 0, 0, 0))
                    src = (cr * ca, cg * ca, cb * ca, ca)
                    pixels[pos] = (src[0] + dst[0] * ica, src[1] + dst[1] * ica, src[2] + dst[2] * ica, src[3] + dst[3] * ica)

    for pos, col in pixels.items():
        ca = col[3]
        if ca:
            pixdata[pos] = tuple(int(round(c)) for c in (col[0] / ca, col[1] / ca, col[2] / ca, ca * 255))


@register('background-noise', 0)
@register('background-noise', 1)
@register('background-noise', 2)
@register('background-noise', 3)
@register('background-noise', 4)
@register('background-noise', 5)
@register('background-noise', 6)
@register('background-noise', 7)
def background_noise(density=None, opacity=None, size=None, monochrome=False, intensity=(), color=None, background=None, inline=False):
    if not Image:
        raise Exception("Images manipulation require PIL")

    density = [Number(v).value for v in List.from_maybe(density)]
    intensity = [Number(v).value for v in List.from_maybe(intensity)]
    color = [Color(v).value for v in List.from_maybe(color) if v]
    opacity = [Number(v).value for v in List.from_maybe(opacity)]

    size = int(Number(size).value) if size else 0
    if size < 1 or size > 512:
        size = 200

    monochrome = bool(monochrome)

    background = Color(background).value if background else None

    new_image = Image.new(
        mode='RGBA',
        size=(size, size)
    )

    pixdata = new_image.load()
    _image_noise(pixdata, size, density, intensity, color, opacity, monochrome)

    if not inline:
        key = (size, density, intensity, color, opacity, monochrome)
        asset_file = 'noise-%s%sx%s' % ('mono-' if monochrome else '', size, size)
        # asset_file += '-[%s][%s]' % ('-'.join(to_str(s).replace('.', '_') for s in density or []), '-'.join(to_str(s).replace('.', '_') for s in opacity or []))
        asset_file += '-' + base64.urlsafe_b64encode(hashlib.md5(repr(key)).digest()).rstrip('=').replace('-', '_')
        asset_file += '.png'
        asset_path = os.path.join(config.ASSETS_ROOT or os.path.join(config.STATIC_ROOT, 'assets'), asset_file)
        try:
            new_image.save(asset_path)
        except IOError:
            log.exception("Error while saving image")
            inline = True  # Retry inline version
        url = '%s%s' % (config.ASSETS_URL, asset_file)
    if inline:
        output = six.BytesIO()
        new_image.save(output, format='PNG')
        contents = output.getvalue()
        output.close()
        url = 'data:image/png;base64,' + base64.b64encode(contents)

    inline = 'url("%s")' % escape(url)
    return String.unquoted(inline)


@register('background-brushed', 0)
@register('background-brushed', 1)
@register('background-brushed', 2)
@register('background-brushed', 3)
@register('background-brushed', 4)
@register('background-brushed', 5)
@register('background-brushed', 6)
@register('background-brushed', 7)
@register('background-brushed', 8)
@register('background-brushed', 9)
def background_brushed(density=None, intensity=None, color=None, opacity=None, size=None, monochrome=False, direction=(), spread=(), background=None, inline=False):
    if not Image:
        raise Exception("Images manipulation require PIL")

    density = [Number(v).value for v in List.from_maybe(density)]
    intensity = [Number(v).value for v in List.from_maybe(intensity)]
    color = [Color(v).value for v in List.from_maybe(color) if v]
    opacity = [Number(v).value for v in List.from_maybe(opacity)]

    size = int(Number(size).value) if size else -1
    if size < 0 or size > 512:
        size = 200

    monochrome = bool(monochrome)

    direction = [Number(v).value for v in List.from_maybe(direction)]
    spread = [Number(v).value for v in List.from_maybe(spread)]

    background = Color(background).value if background else None

    new_image = Image.new(
        mode='RGBA',
        size=(size, size)
    )

    pixdata = new_image.load()
    _image_brushed(pixdata, size, density, intensity, color, opacity, monochrome, direction, spread, background)

    if not inline:
        key = (size, density, intensity, color, opacity, monochrome, direction, spread, background)
        asset_file = 'brushed-%s%sx%s' % ('mono-' if monochrome else '', size, size)
        # asset_file += '-[%s][%s][%s]' % ('-'.join(to_str(s).replace('.', '_') for s in density or []), '-'.join(to_str(s).replace('.', '_') for s in opacity or []), '-'.join(to_str(s).replace('.', '_') for s in direction or []))
        asset_file += '-' + base64.urlsafe_b64encode(hashlib.md5(repr(key)).digest()).rstrip('=').replace('-', '_')
        asset_file += '.png'
        asset_path = os.path.join(config.ASSETS_ROOT or os.path.join(config.STATIC_ROOT, 'assets'), asset_file)
        try:
            new_image.save(asset_path)
        except IOError:
            log.exception("Error while saving image")
            inline = True  # Retry inline version
        url = '%s%s' % (config.ASSETS_URL, asset_file)
    if inline:
        output = six.BytesIO()
        new_image.save(output, format='PNG')
        contents = output.getvalue()
        output.close()
        url = 'data:image/png;base64,' + base64.b64encode(contents)

    inline = 'url("%s")' % escape(url)
    return String.unquoted(inline)


@register('grid-image', 4)
@register('grid-image', 5)
def _grid_image(left_gutter, width, right_gutter, height, columns=1, grid_color=None, baseline_color=None, background_color=None, inline=False):
    if not Image:
        raise Exception("Images manipulation require PIL")
    if grid_color is None:
        grid_color = (120, 170, 250, 15)
    else:
        c = Color(grid_color).value
        grid_color = (c[0], c[1], c[2], int(c[3] * 255.0))
    if baseline_color is None:
        baseline_color = (120, 170, 250, 30)
    else:
        c = Color(baseline_color).value
        baseline_color = (c[0], c[1], c[2], int(c[3] * 255.0))
    if background_color is None:
        background_color = (0, 0, 0, 0)
    else:
        c = Color(background_color).value
        background_color = (c[0], c[1], c[2], int(c[3] * 255.0))
    _height = int(height) if height >= 1 else int(height * 1000.0)
    _width = int(width) if width >= 1 else int(width * 1000.0)
    _left_gutter = int(left_gutter) if left_gutter >= 1 else int(left_gutter * 1000.0)
    _right_gutter = int(right_gutter) if right_gutter >= 1 else int(right_gutter * 1000.0)
    if _height <= 0 or _width <= 0 or _left_gutter <= 0 or _right_gutter <= 0:
        raise ValueError
    _full_width = (_left_gutter + _width + _right_gutter)
    new_image = Image.new(
        mode='RGBA',
        size=(_full_width * int(columns), _height),
        color=background_color
    )
    draw = ImageDraw.Draw(new_image)
    for i in range(int(columns)):
        draw.rectangle((i * _full_width + _left_gutter, 0, i * _full_width + _left_gutter + _width - 1, _height - 1),  fill=grid_color)
    if _height > 1:
        draw.rectangle((0, _height - 1, _full_width * int(columns) - 1, _height - 1),  fill=baseline_color)
    if not inline:
        grid_name = 'grid_'
        if left_gutter:
            grid_name += str(int(left_gutter)) + '+'
        grid_name += str(int(width))
        if right_gutter:
            grid_name += '+' + str(int(right_gutter))
        if height and height > 1:
            grid_name += 'x' + str(int(height))
        key = (columns, grid_color, baseline_color, background_color)
        key = grid_name + '-' + base64.urlsafe_b64encode(hashlib.md5(repr(key)).digest()).rstrip('=').replace('-', '_')
        asset_file = key + '.png'
        asset_path = os.path.join(config.ASSETS_ROOT or os.path.join(config.STATIC_ROOT, 'assets'), asset_file)
        try:
            new_image.save(asset_path)
        except IOError:
            log.exception("Error while saving image")
            inline = True  # Retry inline version
        url = '%s%s' % (config.ASSETS_URL, asset_file)
    if inline:
        output = six.BytesIO()
        new_image.save(output, format='PNG')
        contents = output.getvalue()
        output.close()
        url = 'data:image/png;base64,' + base64.b64encode(contents)
    inline = 'url("%s")' % escape(url)
    return String.unquoted(inline)


@register('image-color', 1)
@register('image-color', 2)
@register('image-color', 3)
def image_color(color, width=1, height=1):
    if not Image:
        raise Exception("Images manipulation require PIL")
    w = int(Number(width).value)
    h = int(Number(height).value)
    if w <= 0 or h <= 0:
        raise ValueError
    new_image = Image.new(
        mode='RGB' if color.alpha == 1 else 'RGBA',
        size=(w, h),
        color=color.rgba255,
    )
    output = six.BytesIO()
    new_image.save(output, format='PNG')
    contents = output.getvalue()
    output.close()
    mime_type = 'image/png'
    url = 'data:' + mime_type + ';base64,' + base64.b64encode(contents)
    inline = 'url("%s")' % escape(url)
    return String.unquoted(inline)
