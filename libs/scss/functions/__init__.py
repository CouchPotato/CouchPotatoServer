from __future__ import absolute_import

from scss.functions.library import FunctionLibrary

from scss.functions.core import CORE_LIBRARY
from scss.functions.extra import EXTRA_LIBRARY
from scss.functions.compass.sprites import COMPASS_SPRITES_LIBRARY
from scss.functions.compass.gradients import COMPASS_GRADIENTS_LIBRARY
from scss.functions.compass.helpers import COMPASS_HELPERS_LIBRARY
from scss.functions.compass.images import COMPASS_IMAGES_LIBRARY


ALL_BUILTINS_LIBRARY = FunctionLibrary()
ALL_BUILTINS_LIBRARY.inherit(
    CORE_LIBRARY,
    EXTRA_LIBRARY,
    COMPASS_GRADIENTS_LIBRARY,
    COMPASS_HELPERS_LIBRARY,
    COMPASS_IMAGES_LIBRARY,
    COMPASS_SPRITES_LIBRARY,
)

# TODO back-compat for the only codebase still using the old name  :)
FunctionRegistry = FunctionLibrary
scss_builtins = ALL_BUILTINS_LIBRARY
