Linktastic

Linktastic is an extension of the os.link and os.symlink functionality provided
by the python language since version 2.  Python only supports file linking on
*NIX-based systems, even though it is relatively simple to engineer a solution
to utilize NTFS's built-in linking functionality.  Linktastic attempts to unify
linking on the windows platform with linking on *NIX-based systems.

Usage

Linktastic is a single python module and can be imported as such.  Examples:

# Hard linking src to dest
import linktastic
linktastic.link(src, dest)

# Symlinking src to dest
import linktastic
linktastic.symlink(src, dest)
