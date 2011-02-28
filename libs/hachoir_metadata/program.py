from hachoir_metadata.metadata import RootMetadata, registerExtractor
from hachoir_parser.program import ExeFile
from hachoir_metadata.safe import fault_tolerant, getValue

class ExeMetadata(RootMetadata):
    KEY_TO_ATTR = {
        u"ProductName": "title",
        u"LegalCopyright": "copyright",
        u"LegalTrademarks": "copyright",
        u"LegalTrademarks1": "copyright",
        u"LegalTrademarks2": "copyright",
        u"CompanyName": "author",
        u"BuildDate": "creation_date",
        u"FileDescription": "title",
        u"ProductVersion": "version",
    }
    SKIP_KEY = set((u"InternalName", u"OriginalFilename", u"FileVersion", u"BuildVersion"))

    def extract(self, exe):
        if exe.isPE():
            self.extractPE(exe)
        elif exe.isNE():
            self.extractNE(exe)

    def extractNE(self, exe):
        if "ne_header" in exe:
            self.useNE_Header(exe["ne_header"])
        if "info" in exe:
            self.useNEInfo(exe["info"])

    @fault_tolerant
    def useNEInfo(self, info):
        for node in info.array("node"):
            if node["name"].value == "StringFileInfo":
                self.readVersionInfo(node["node[0]"])

    def extractPE(self, exe):
        # Read information from headers
        if "pe_header" in exe:
            self.usePE_Header(exe["pe_header"])
        if "pe_opt_header" in exe:
            self.usePE_OptHeader(exe["pe_opt_header"])

        # Use PE resource
        resource = exe.getResource()
        if resource and "version_info/node[0]" in resource:
            for node in resource.array("version_info/node[0]/node"):
                if getValue(node, "name") == "StringFileInfo" \
                and "node[0]" in node:
                    self.readVersionInfo(node["node[0]"])

    @fault_tolerant
    def useNE_Header(self, hdr):
        if hdr["is_dll"].value:
            self.format_version = u"New-style executable: Dynamic-link library (DLL)"
        elif hdr["is_win_app"].value:
            self.format_version = u"New-style executable: Windows 3.x application"
        else:
            self.format_version = u"New-style executable for Windows 3.x"

    @fault_tolerant
    def usePE_Header(self, hdr):
        self.creation_date = hdr["creation_date"].value
        self.comment = "CPU: %s" % hdr["cpu"].display
        if hdr["is_dll"].value:
            self.format_version = u"Portable Executable: Dynamic-link library (DLL)"
        else:
            self.format_version = u"Portable Executable: Windows application"

    @fault_tolerant
    def usePE_OptHeader(self, hdr):
        self.comment = "Subsystem: %s" % hdr["subsystem"].display

    def readVersionInfo(self, info):
        values = {}
        for node in info.array("node"):
            if "value" not in node or "name" not in node:
                continue
            value = node["value"].value.strip(" \0")
            if not value:
                continue
            key = node["name"].value
            values[key] = value

        if "ProductName" in values and "FileDescription" in values:
            # Make sure that FileDescription is set before ProductName
            # as title value
            self.title = values["FileDescription"]
            self.title = values["ProductName"]
            del values["FileDescription"]
            del values["ProductName"]

        for key, value in values.iteritems():
            if key in self.KEY_TO_ATTR:
                setattr(self, self.KEY_TO_ATTR[key], value)
            elif key not in self.SKIP_KEY:
                self.comment = "%s=%s" % (key, value)

registerExtractor(ExeFile, ExeMetadata)

