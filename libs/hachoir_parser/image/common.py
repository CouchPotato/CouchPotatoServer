from hachoir_core.field import FieldSet, UserVector, UInt8

class RGB(FieldSet):
    color_name = {
        (  0,   0,   0): "Black",
        (255,   0,   0): "Red",
        (  0, 255,   0): "Green",
        (  0,   0, 255): "Blue",
        (255, 255, 255): "White",
    }
    static_size = 24

    def createFields(self):
        yield UInt8(self, "red", "Red")
        yield UInt8(self, "green", "Green")
        yield UInt8(self, "blue", "Blue")

    def createDescription(self):
        rgb = self["red"].value, self["green"].value, self["blue"].value
        name = self.color_name.get(rgb)
        if not name:
            name = "#%02X%02X%02X" % rgb
        return "RGB color: " + name

class RGBA(RGB):
    static_size = 32

    def createFields(self):
        yield UInt8(self, "red", "Red")
        yield UInt8(self, "green", "Green")
        yield UInt8(self, "blue", "Blue")
        yield UInt8(self, "alpha", "Alpha")

    def createDescription(self):
        description = RGB.createDescription(self)
        opacity = self["alpha"].value*100/255
        return "%s (opacity: %s%%)" % (description, opacity)

class PaletteRGB(UserVector):
    item_class = RGB
    item_name = "color"
    def createDescription(self):
        return "Palette of %u RGB colors" % len(self)

class PaletteRGBA(PaletteRGB):
    item_class = RGBA
    def createDescription(self):
        return "Palette of %u RGBA colors" % len(self)

