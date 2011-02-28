from hachoir_metadata.version import VERSION as __version__
from hachoir_metadata.metadata import extractMetadata

# Just import the module,
# each module use registerExtractor() method
import hachoir_metadata.archive
import hachoir_metadata.audio
import hachoir_metadata.file_system
import hachoir_metadata.image
import hachoir_metadata.jpeg
import hachoir_metadata.misc
import hachoir_metadata.program
import hachoir_metadata.riff
import hachoir_metadata.video

