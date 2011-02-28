"""
Configuration of Hachoir
"""

import os

# UI: display options
max_string_length = 40    # Max. length in characters of GenericString.display
max_byte_length = 14      # Max. length in bytes of RawBytes.display
max_bit_length = 256      # Max. length in bits of RawBits.display
unicode_stdout = True     # Replace stdout and stderr with Unicode compatible objects
                          # Disable it for readline or ipython

# Global options
debug = False             # Display many informations usefull to debug
verbose = False           # Display more informations
quiet = False             # Don't display warnings

# Use internationalization and localization (gettext)?
if os.name == "nt":
    # TODO: Remove this hack and make i18n works on Windows :-)
    use_i18n = False
else:
    use_i18n = True

# Parser global options
autofix = True            # Enable Autofix? see hachoir_core.field.GenericFieldSet
check_padding_pattern = True   # Check padding fields pattern?

