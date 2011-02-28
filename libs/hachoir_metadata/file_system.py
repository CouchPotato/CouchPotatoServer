from hachoir_metadata.metadata import RootMetadata, registerExtractor
from hachoir_metadata.safe import fault_tolerant
from hachoir_parser.file_system import ISO9660
from datetime import datetime

class ISO9660_Metadata(RootMetadata):
    def extract(self, iso):
        desc = iso['volume[0]/content']
        self.title = desc['volume_id'].value
        self.title = desc['vol_set_id'].value
        self.author = desc['publisher'].value
        self.author = desc['data_preparer'].value
        self.producer = desc['application'].value
        self.copyright = desc['copyright'].value
        self.readTimestamp('creation_date', desc['creation_ts'].value)
        self.readTimestamp('last_modification', desc['modification_ts'].value)

    @fault_tolerant
    def readTimestamp(self, key, value):
        if value.startswith("0000"):
            return
        value = datetime(
            int(value[0:4]), int(value[4:6]), int(value[6:8]),
            int(value[8:10]), int(value[10:12]), int(value[12:14]))
        setattr(self, key, value)

registerExtractor(ISO9660, ISO9660_Metadata)

