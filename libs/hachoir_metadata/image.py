from hachoir_metadata.metadata import (registerExtractor,
    Metadata, RootMetadata, MultipleMetadata)
from hachoir_parser.image import (
    BmpFile, IcoFile, PcxFile, GifFile, PngFile, TiffFile,
    XcfFile, TargaFile, WMF_File, PsdFile)
from hachoir_parser.image.png import getBitsPerPixel as pngBitsPerPixel
from hachoir_parser.image.xcf import XcfProperty
from hachoir_core.i18n import _
from hachoir_metadata.safe import fault_tolerant

def computeComprRate(meta, compr_size):
    """
    Compute image compression rate. Skip size of color palette, focus on
    image pixels. Original size is width x height x bpp. Compressed size
    is an argument (in bits).

    Set "compr_data" with a string like "1.52x".
    """
    if not meta.has("width") \
    or not meta.has("height") \
    or not meta.has("bits_per_pixel"):
        return
    if not compr_size:
        return
    orig_size = meta.get('width') * meta.get('height') * meta.get('bits_per_pixel')
    meta.compr_rate = float(orig_size) / compr_size

class BmpMetadata(RootMetadata):
    def extract(self, image):
        if "header" not in image:
            return
        hdr = image["header"]
        self.width = hdr["width"].value
        self.height = hdr["height"].value
        bpp = hdr["bpp"].value
        if bpp:
            if bpp <= 8 and "used_colors" in hdr:
                self.nb_colors = hdr["used_colors"].value
            self.bits_per_pixel = bpp
        self.compression = hdr["compression"].display
        self.format_version = u"Microsoft Bitmap version %s" % hdr.getFormatVersion()

        self.width_dpi = hdr["horizontal_dpi"].value
        self.height_dpi = hdr["vertical_dpi"].value

        if "pixels" in image:
            computeComprRate(self, image["pixels"].size)

class TiffMetadata(RootMetadata):
    key_to_attr = {
        "img_width": "width",
        "img_height": "width",

        # TODO: Enable that (need link to value)
#        "description": "comment",
#        "doc_name": "title",
#        "orientation": "image_orientation",
    }
    def extract(self, tiff):
        if "ifd" in tiff:
            self.useIFD(tiff["ifd"])

    def useIFD(self, ifd):
        for field in ifd:
            try:
                attrname = self.key_to_attr[field.name]
            except KeyError:
                continue
            if "value" not in field:
                continue
            value = field["value"].value
            setattr(self, attrname, value)

class IcoMetadata(MultipleMetadata):
    color_to_bpp = {
        2: 1,
        16: 4,
        256: 8
    }

    def extract(self, icon):
        for index, header in enumerate(icon.array("icon_header")):
            image = Metadata(self)

            # Read size and colors from header
            image.width = header["width"].value
            image.height = header["height"].value
            bpp = header["bpp"].value
            nb_colors = header["nb_color"].value
            if nb_colors != 0:
                image.nb_colors = nb_colors
                if bpp == 0 and nb_colors in self.color_to_bpp:
                    bpp = self.color_to_bpp[nb_colors]
            elif bpp == 0:
                bpp = 8
            image.bits_per_pixel = bpp
            image.setHeader(_("Icon #%u (%sx%s)")
                % (1+index, image.get("width", "?"), image.get("height", "?")))

            # Read compression from data (if available)
            key = "icon_data[%u]/header/codec" % index
            if key in icon:
                image.compression = icon[key].display
            key = "icon_data[%u]/pixels" % index
            if key in icon:
                computeComprRate(image, icon[key].size)

            # Store new image
            self.addGroup("image[%u]" % index, image)

class PcxMetadata(RootMetadata):
    @fault_tolerant
    def extract(self, pcx):
        self.width = 1 + pcx["xmax"].value
        self.height = 1 + pcx["ymax"].value
        self.width_dpi = pcx["horiz_dpi"].value
        self.height_dpi = pcx["vert_dpi"].value
        self.bits_per_pixel = pcx["bpp"].value
        if 1 <= pcx["bpp"].value <= 8:
            self.nb_colors = 2 ** pcx["bpp"].value
        self.compression = _("Run-length encoding (RLE)")
        self.format_version = "PCX: %s" % pcx["version"].display
        if "image_data" in pcx:
            computeComprRate(self, pcx["image_data"].size)

class XcfMetadata(RootMetadata):
    # Map image type to bits/pixel
    TYPE_TO_BPP = {0: 24, 1: 8, 2: 8}

    def extract(self, xcf):
        self.width = xcf["width"].value
        self.height = xcf["height"].value
        try:
            self.bits_per_pixel = self.TYPE_TO_BPP[ xcf["type"].value ]
        except KeyError:
            pass
        self.format_version = xcf["type"].display
        self.readProperties(xcf)

    @fault_tolerant
    def processProperty(self, prop):
        type = prop["type"].value
        if type == XcfProperty.PROP_PARASITES:
            for field in prop["data"]:
                if "name" not in field or "data" not in field:
                    continue
                if field["name"].value == "gimp-comment":
                    self.comment = field["data"].value
        elif type == XcfProperty.PROP_COMPRESSION:
            self.compression = prop["data/compression"].display
        elif type == XcfProperty.PROP_RESOLUTION:
            self.width_dpi = int(prop["data/xres"].value)
            self.height_dpi = int(prop["data/yres"].value)

    def readProperties(self, xcf):
        for prop in xcf.array("property"):
            self.processProperty(prop)

class PngMetadata(RootMetadata):
    TEXT_TO_ATTR = {
        "software": "producer",
    }

    def extract(self, png):
        if "header" in png:
            self.useHeader(png["header"])
        if "time" in png:
            self.useTime(png["time"])
        if "physical" in png:
            self.usePhysical(png["physical"])
        for comment in png.array("text"):
            if "text" not in comment:
                continue
            keyword = comment["keyword"].value
            text = comment["text"].value
            try:
                key = self.TEXT_TO_ATTR[keyword.lower()]
                setattr(self, key, text)
            except KeyError:
                if keyword.lower() != "comment":
                    self.comment = "%s=%s" % (keyword, text)
                else:
                    self.comment = text
        compr_size = sum( data.size for data in png.array("data") )
        computeComprRate(self, compr_size)

    @fault_tolerant
    def useTime(self, field):
        self.creation_date = field.value

    @fault_tolerant
    def usePhysical(self, field):
        self.width_dpi = field["pixel_per_unit_x"].value
        self.height_dpi = field["pixel_per_unit_y"].value

    @fault_tolerant
    def useHeader(self, header):
        self.width = header["width"].value
        self.height = header["height"].value

        # Read number of colors and pixel format
        if "/palette/size" in header:
            nb_colors = header["/palette/size"].value // 3
        else:
            nb_colors = None
        if not header["has_palette"].value:
            if header["has_alpha"].value:
                self.pixel_format = _("RGBA")
            else:
                self.pixel_format = _("RGB")
        elif "/transparency" in header:
            self.pixel_format = _("Color index with transparency")
            if nb_colors:
                nb_colors -= 1
        else:
            self.pixel_format = _("Color index")
        self.bits_per_pixel = pngBitsPerPixel(header)
        if nb_colors:
            self.nb_colors = nb_colors

        # Read compression, timestamp, etc.
        self.compression = header["compression"].display

class GifMetadata(RootMetadata):
    def extract(self, gif):
        self.useScreen(gif["/screen"])
        if self.has("bits_per_pixel"):
            self.nb_colors = (1 << self.get('bits_per_pixel'))
        self.compression = _("LZW")
        self.format_version =  "GIF version %s" % gif["version"].value
        for comments in gif.array("comments"):
            for comment in gif.array(comments.name + "/comment"):
                self.comment = comment.value
        if "graphic_ctl/has_transp" in gif and gif["graphic_ctl/has_transp"].value:
            self.pixel_format = _("Color index with transparency")
        else:
            self.pixel_format = _("Color index")

    @fault_tolerant
    def useScreen(self, screen):
        self.width = screen["width"].value
        self.height = screen["height"].value
        self.bits_per_pixel = (1 + screen["bpp"].value)

class TargaMetadata(RootMetadata):
    def extract(self, tga):
        self.width = tga["width"].value
        self.height = tga["height"].value
        self.bits_per_pixel = tga["bpp"].value
        if tga["nb_color"].value:
            self.nb_colors = tga["nb_color"].value
        self.compression = tga["codec"].display
        if "pixels" in tga:
            computeComprRate(self, tga["pixels"].size)

class WmfMetadata(RootMetadata):
    def extract(self, wmf):
        if wmf.isAPM():
            if "amf_header/rect" in wmf:
                rect = wmf["amf_header/rect"]
                self.width = (rect["right"].value - rect["left"].value)
                self.height = (rect["bottom"].value - rect["top"].value)
            self.bits_per_pixel = 24
        elif wmf.isEMF():
            emf = wmf["emf_header"]
            if "description" in emf:
                desc = emf["description"].value
                if "\0" in desc:
                    self.producer, self.title = desc.split("\0", 1)
                else:
                    self.producer = desc
            if emf["nb_colors"].value:
                self.nb_colors = emf["nb_colors"].value
                self.bits_per_pixel = 8
            else:
                self.bits_per_pixel = 24
            self.width = emf["width_px"].value
            self.height = emf["height_px"].value

class PsdMetadata(RootMetadata):
    @fault_tolerant
    def extract(self, psd):
        self.width = psd["width"].value
        self.height = psd["height"].value
        self.bits_per_pixel = psd["depth"].value * psd["nb_channels"].value
        self.pixel_format = psd["color_mode"].display
        self.compression = psd["compression"].display

registerExtractor(IcoFile, IcoMetadata)
registerExtractor(GifFile, GifMetadata)
registerExtractor(XcfFile, XcfMetadata)
registerExtractor(TargaFile, TargaMetadata)
registerExtractor(PcxFile, PcxMetadata)
registerExtractor(BmpFile, BmpMetadata)
registerExtractor(PngFile, PngMetadata)
registerExtractor(TiffFile, TiffMetadata)
registerExtractor(WMF_File, WmfMetadata)
registerExtractor(PsdFile, PsdMetadata)

