"""Functions used for generating packed CSS sprite maps.


These are ported from the Binary Tree Bin Packing Algorithm:
http://codeincomplete.com/posts/2011/5/7/bin_packing/
"""

# Copyright (c) 2011, 2012, 2013 Jake Gordon and contributors
# Copyright (c) 2013 German M. Bravo

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


class LayoutNode(object):
    def __init__(self, x, y, w, h, down=None, right=None, used=False):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.down = down
        self.right = right
        self.used = used
        self.width = 0
        self.height = 0

    @property
    def area(self):
        return self.width * self.height

    def __repr__(self):
        return '<%s (%s, %s) [%sx%s]>' % (self.__class__.__name__, self.x, self.y, self.w, self.h)


class SpritesLayout(object):
    def __init__(self, blocks, padding=None, margin=None, ppadding=None, pmargin=None):
        self.num_blocks = len(blocks)

        if margin is None:
            margin = [[0] * 4] * self.num_blocks
        elif not isinstance(margin, (tuple, list)):
            margin = [[margin] * 4] * self.num_blocks
        elif not isinstance(margin[0], (tuple, list)):
            margin = [margin] * self.num_blocks

        if padding is None:
            padding = [[0] * 4] * self.num_blocks
        elif not isinstance(padding, (tuple, list)):
            padding = [[padding] * 4] * self.num_blocks
        elif not isinstance(padding[0], (tuple, list)):
            padding = [padding] * self.num_blocks

        if pmargin is None:
            pmargin = [[0.0] * 4] * self.num_blocks
        elif not isinstance(pmargin, (tuple, list)):
            pmargin = [[pmargin] * 4] * self.num_blocks
        elif not isinstance(pmargin[0], (tuple, list)):
            pmargin = [pmargin] * self.num_blocks

        if ppadding is None:
            ppadding = [[0.0] * 4] * self.num_blocks
        elif not isinstance(ppadding, (tuple, list)):
            ppadding = [[ppadding] * 4] * self.num_blocks
        elif not isinstance(ppadding[0], (tuple, list)):
            ppadding = [ppadding] * self.num_blocks

        self.blocks = tuple((
            b[0] + padding[i][3] + padding[i][1] + margin[i][3] + margin[i][1] + int(round(b[0] * (ppadding[i][3] + ppadding[i][1] + pmargin[i][3] + pmargin[i][1]))),
            b[1] + padding[i][0] + padding[i][2] + margin[i][0] + margin[i][2] + int(round(b[1] * (ppadding[i][0] + ppadding[i][2] + pmargin[i][0] + pmargin[i][2]))),
            b[0],
            b[1],
            i
        ) for i, b in enumerate(blocks))

        self.margin = margin
        self.padding = padding
        self.pmargin = pmargin
        self.ppadding = ppadding


class PackedSpritesLayout(SpritesLayout):
    @staticmethod
    def MAXSIDE(a, b):
        """maxside: Sort pack by maximum sides"""
        return cmp(max(b[0], b[1]), max(a[0], a[1])) or cmp(min(b[0], b[1]), min(a[0], a[1])) or cmp(b[1], a[1]) or cmp(b[0], a[0])

    @staticmethod
    def WIDTH(a, b):
        """width: Sort pack by width"""
        return cmp(b[0], a[0]) or cmp(b[1], a[1])

    @staticmethod
    def HEIGHT(a, b):
        """height: Sort pack by height"""
        return cmp(b[1], a[1]) or cmp(b[0], a[0])

    @staticmethod
    def AREA(a, b):
        """area: Sort pack by area"""
        return cmp(b[0] * b[1], a[0] * a[1]) or cmp(b[1], a[1]) or cmp(b[0], a[0])

    def __init__(self, blocks, padding=None, margin=None, ppadding=None, pmargin=None, methods=None):
        super(PackedSpritesLayout, self).__init__(blocks, padding, margin, ppadding, pmargin)

        ratio = 0

        if methods is None:
            methods = (self.MAXSIDE, self.WIDTH, self.HEIGHT, self.AREA)

        for method in methods:
            sorted_blocks = sorted(
                self.blocks,
                cmp=method,
            )
            root = LayoutNode(
                x=0,
                y=0,
                w=sorted_blocks[0][0] if sorted_blocks else 0,
                h=sorted_blocks[0][1] if sorted_blocks else 0
            )

            area = 0
            nodes = [None] * self.num_blocks

            for block in sorted_blocks:
                w, h, width, height, i = block
                node = self._findNode(root, w, h)
                if node:
                    node = self._splitNode(node, w, h)
                else:
                    root = self._growNode(root, w, h)
                    node = self._findNode(root, w, h)
                    if node:
                        node = self._splitNode(node, w, h)
                    else:
                        node = None
                nodes[i] = node
                node.width = width
                node.height = height
                area += node.area

            this_ratio = area / float(root.w * root.h)
            # print method.__doc__, "%g%%" % (this_ratio * 100)
            if ratio < this_ratio:
                self.root = root
                self.nodes = nodes
                self.method = method
                ratio = this_ratio
                if ratio > 0.96:
                    break
        # print self.method.__doc__, "%g%%" % (ratio * 100)

    def __iter__(self):
        for i, node in enumerate(self.nodes):
            margin, padding = self.margin[i], self.padding[i]
            pmargin, ppadding = self.pmargin[i], self.ppadding[i]
            cssw = node.width + padding[3] + padding[1] + int(round(node.width * (ppadding[3] + ppadding[1])))  # image width plus padding
            cssh = node.height + padding[0] + padding[2] + int(round(node.height * (ppadding[0] + ppadding[2])))  # image height plus padding
            cssx = node.x + margin[3] + int(round(node.width * pmargin[3]))
            cssy = node.y + margin[0] + int(round(node.height * pmargin[0]))
            x = cssx + padding[3] + int(round(node.width * ppadding[3]))
            y = cssy + padding[0] + int(round(node.height * ppadding[0]))
            yield x, y, node.width, node.height, cssx, cssy, cssw, cssh

    @property
    def width(self):
        return self.root.w

    @property
    def height(self):
        return self.root.h

    def _findNode(self, root, w, h):
        if root.used:
            return self._findNode(root.right, w, h) or self._findNode(root.down, w, h)
        elif w <= root.w and h <= root.h:
            return root
        else:
            return None

    def _splitNode(self, node, w, h):
        node.used = True
        node.down = LayoutNode(
            x=node.x,
            y=node.y + h,
            w=node.w,
            h=node.h - h
        )
        node.right = LayoutNode(
            x=node.x + w,
            y=node.y,
            w=node.w - w,
            h=h
        )
        return node

    def _growNode(self, root, w, h):
        canGrowDown = w <= root.w
        canGrowRight = h <= root.h

        shouldGrowRight = canGrowRight and (root.h >= root.w + w)  # attempt to keep square-ish by growing right when height is much greater than width
        shouldGrowDown = canGrowDown and (root.w >= root.h + h)  # attempt to keep square-ish by growing down when width is much greater than height

        if shouldGrowRight:
            return self._growRight(root, w, h)
        elif shouldGrowDown:
            return self._growDown(root, w, h)
        elif canGrowRight:
            return self._growRight(root, w, h)
        elif canGrowDown:
            return self._growDown(root, w, h)
        else:
            # need to ensure sensible root starting size to avoid this happening
            assert False, "Blocks must be properly sorted!"

    def _growRight(self, root, w, h):
        root = LayoutNode(
            used=True,
            x=0,
            y=0,
            w=root.w + w,
            h=root.h,
            down=root,
            right=LayoutNode(
                x=root.w,
                y=0,
                w=w,
                h=root.h
            )
        )
        return root

    def _growDown(self, root, w, h):
        root = LayoutNode(
            used=True,
            x=0,
            y=0,
            w=root.w,
            h=root.h + h,
            down=LayoutNode(
                x=0,
                y=root.h,
                w=root.w,
                h=h
            ),
            right=root
        )
        return root


class HorizontalSpritesLayout(SpritesLayout):
    def __init__(self, blocks, padding=None, margin=None, ppadding=None, pmargin=None, position=None):
        super(HorizontalSpritesLayout, self).__init__(blocks, padding, margin, ppadding, pmargin)

        self.width = sum(zip(*self.blocks)[0])
        self.height = max(zip(*self.blocks)[1])

        if position is None:
            position = [0.0] * self.num_blocks
        elif not isinstance(position, (tuple, list)):
            position = [position] * self.num_blocks
        self.position = position

    def __iter__(self):
        cx = 0
        for i, block in enumerate(self.blocks):
            w, h, width, height, i = block
            margin, padding = self.margin[i], self.padding[i]
            pmargin, ppadding = self.pmargin[i], self.ppadding[i]
            position = self.position[i]
            cssw = width + padding[3] + padding[1] + int(round(width * (ppadding[3] + ppadding[1])))  # image width plus padding
            cssh = height + padding[0] + padding[2] + int(round(height * (ppadding[0] + ppadding[2])))  # image height plus padding
            cssx = cx + margin[3] + int(round(width * pmargin[3]))  # anchored at x
            cssy = int(round((self.height - cssh) * position))  # centered vertically
            x = cssx + padding[3] + int(round(width * ppadding[3]))  # image drawn offset to account for padding
            y = cssy + padding[0] + int(round(height * ppadding[0]))  # image drawn offset to account for padding
            yield x, y, width, height, cssx, cssy, cssw, cssh
            cx += cssw + margin[3] + margin[1] + int(round(width * (pmargin[3] + pmargin[1])))


class VerticalSpritesLayout(SpritesLayout):
    def __init__(self, blocks, padding=None, margin=None, ppadding=None, pmargin=None, position=None):
        super(VerticalSpritesLayout, self).__init__(blocks, padding, margin, ppadding, pmargin)

        self.width = max(zip(*self.blocks)[0])
        self.height = sum(zip(*self.blocks)[1])

        if position is None:
            position = [0.0] * self.num_blocks
        elif not isinstance(position, (tuple, list)):
            position = [position] * self.num_blocks
        self.position = position

    def __iter__(self):
        cy = 0
        for i, block in enumerate(self.blocks):
            w, h, width, height, i = block
            margin, padding = self.margin[i], self.padding[i]
            pmargin, ppadding = self.pmargin[i], self.ppadding[i]
            position = self.position[i]
            cssw = width + padding[3] + padding[1] + int(round(width * (ppadding[3] + ppadding[1])))  # image width plus padding
            cssh = height + padding[0] + padding[2] + int(round(height * (ppadding[0] + ppadding[2])))  # image height plus padding
            cssx = int(round((self.width - cssw) * position))  # centered horizontally
            cssy = cy + margin[0] + int(round(height * pmargin[0]))  # anchored at y
            x = cssx + padding[3] + int(round(width * ppadding[3]))  # image drawn offset to account for padding
            y = cssy + padding[0] + int(round(height * ppadding[0]))  # image drawn offset to account for padding
            yield x, y, width, height, cssx, cssy, cssw, cssh
            cy += cssh + margin[0] + margin[2] + int(round(height * (pmargin[0] + pmargin[2])))


class DiagonalSpritesLayout(SpritesLayout):
    def __init__(self, blocks, padding=None, margin=None, ppadding=None, pmargin=None):
        super(DiagonalSpritesLayout, self).__init__(blocks, padding, margin, ppadding, pmargin)
        self.width = sum(zip(*self.blocks)[0])
        self.height = sum(zip(*self.blocks)[1])

    def __iter__(self):
        cx, cy = 0, 0
        for i, block in enumerate(self.blocks):
            w, h, width, height, i = block
            margin, padding = self.margin[i], self.padding[i]
            pmargin, ppadding = self.pmargin[i], self.ppadding[i]
            cssw = width + padding[3] + padding[1] + int(round(width * (ppadding[3] + ppadding[1])))  # image width plus padding
            cssh = height + padding[0] + padding[2] + int(round(height * (ppadding[0] + ppadding[2])))  # image height plus padding
            cssx = cx + margin[3] + int(round(width * pmargin[3]))  # anchored at x
            cssy = cy + margin[0] + int(round(height * pmargin[0]))  # anchored at y
            x = cssx + padding[3] + int(round(width * ppadding[3]))  # image drawn offset to account for padding
            y = cssy + padding[0] + int(round(height * ppadding[0]))  # image drawn offset to account for padding
            yield x, y, width, height, cssx, cssy, cssw, cssh
            cx += cssw + margin[3] + margin[1] + int(round(width * (pmargin[3] + pmargin[1])))
            cy += cssh + margin[0] + margin[2] + int(round(height * (pmargin[0] + pmargin[2])))
