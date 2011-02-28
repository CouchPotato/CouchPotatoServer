from hachoir_core.field import StaticFieldSet, Float32

class Vertex(StaticFieldSet):
    format = ((Float32, "x"), (Float32, "y"), (Float32, "z"))

    def createValue(self):
        return (self["x"].value, self["y"].value, self["z"].value)

class MapUV(StaticFieldSet):
    format = ((Float32, "u"), (Float32, "v"))

    def createValue(self):
        return (self["u"].value, self["v"].value)
