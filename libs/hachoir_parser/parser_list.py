import re
import types
from hachoir_core.error import error
from hachoir_core.i18n import _
from hachoir_parser import Parser, HachoirParser
import sys

### Parser list ################################################################

class ParserList(object):
    VALID_CATEGORY = ("archive", "audio", "container", "file_system",
        "game", "image", "misc", "program", "video")
    ID_REGEX = re.compile("^[a-z0-9][a-z0-9_]{2,}$")

    def __init__(self):
        self.parser_list = []
        self.bytag = { "id": {}, "category": {} }

    def translate(self, name, value):
        if name in ("magic",):
            return True
        elif name == "min_size":
            return - value < 0 or "Invalid minimum size (min_size)"
        elif name == "description":
            return isinstance(value, (str, unicode)) and bool(value) or "Invalid description"
        elif name == "category":
            if value not in self.VALID_CATEGORY:
                return "Invalid category: %r" % value
        elif name == "id":
            if type(value) is not str or not self.ID_REGEX.match(value):
                return "Invalid identifier: %r" % value
            parser = self.bytag[name].get(value)
            if parser:
                return "Duplicate parser id: %s already used by %s" % \
                    (value, parser[0].__name__)
        # TODO: lists should be forbidden
        if isinstance(value, list):
            value = tuple(value)
        elif not isinstance(value, tuple):
            value = value,
        return name, value

    def validParser(self, parser, tags):
        if "id" not in tags:
            return "No identifier"
        if "description" not in tags:
            return "No description"
        # TODO: Allow simple strings for file_ext/mime ?
        # (see also HachoirParser.createFilenameSuffix)
        file_ext = tags.get("file_ext", ())
        if not isinstance(file_ext, (tuple, list)):
            return "File extension is not a tuple or list"
        mimes = tags.get("mime", ())
        if not isinstance(mimes, tuple):
            return "MIME type is not a tuple"
        for mime in mimes:
            if not isinstance(mime, unicode):
                return "MIME type %r is not an unicode string" % mime

        return ""

    def add(self, parser):
        tags = parser.getParserTags()
        err = self.validParser(parser, tags)
        if err:
            error("Skip parser %s: %s" % (parser.__name__, err))
            return

        _tags = []
        for tag in tags.iteritems():
            tag = self.translate(*tag)
            if isinstance(tag, tuple):
                _tags.append(tag)
            elif tag is not True:
                error("[%s] %s" % (parser.__name__, tag))
                return

        self.parser_list.append(parser)

        for name, values in _tags:
            byname = self.bytag.setdefault(name,{})
            for value in values:
                byname.setdefault(value,[]).append(parser)

    def __iter__(self):
        return iter(self.parser_list)

    def print_(self, title=None, out=None, verbose=False, format="one-line"):
        """Display a list of parser with its title
         * out: output file
         * title : title of the list to display
         * format: "rest", "trac", "file-ext", "mime" or "one_line" (default)
        """
        if out is None:
            out = sys.stdout

        if format in ("file-ext", "mime"):
            # Create file extension set
            extensions = set()
            for parser in self:
                file_ext = parser.getParserTags().get(format, ())
                file_ext = list(file_ext)
                try:
                    file_ext.remove("")
                except ValueError:
                    pass
                extensions |= set(file_ext)

            # Remove empty extension
            extensions -= set(('',))

            # Convert to list and sort by ASCII order
            extensions = list(extensions)
            extensions.sort()

            # Print list
            text = ", ".join( str(item) for item in extensions )
            if format == "file-ext":
                print >>out, "File extensions: %s." % text
                print >>out
                print >>out, "Total: %s file extensions." % len(extensions)
            else:
                print >>out, "MIME types: %s." % text
                print >>out
                print >>out, "Total: %s MIME types." % len(extensions)
            return

        if format == "trac":
            print >>out, "== List of parsers =="
            print >>out
            print >>out, "Total: %s parsers" % len(self.parser_list)
            print >>out
        elif format == "one_line":
            if title:
                print >>out, title
            else:
                print >>out, _("List of Hachoir parsers.")
            print >>out

        # Create parser list sorted by module
        bycategory = self.bytag["category"]
        for category in sorted(bycategory.iterkeys()):
            if format == "one_line":
                parser_list = [ parser.PARSER_TAGS["id"] for parser in bycategory[category] ]
                parser_list.sort()
                print >>out, "- %s: %s" % (category.title(), ", ".join(parser_list))
            else:
                if format == "rest":
                    print >>out, category.replace("_", " ").title()
                    print >>out, "-" * len(category)
                    print >>out
                elif format == "trac":
                    print >>out, "=== %s ===" % category.replace("_", " ").title()
                    print >>out
                else:
                    print >>out, "[%s]" % category
                parser_list = sorted(bycategory[category],
                    key=lambda parser: parser.PARSER_TAGS["id"])
                if format == "rest":
                    for parser in parser_list:
                        tags = parser.getParserTags()
                        print >>out, "* %s: %s" % (tags["id"], tags["description"])
                elif format == "trac":
                    for parser in parser_list:
                        tags = parser.getParserTags()
                        desc = tags["description"]
                        desc = re.sub(r"([A-Z][a-z]+[A-Z][^ ]+)", r"!\1", desc)
                        print >>out, " * %s: %s" % (tags["id"], desc)
                else:
                    for parser in parser_list:
                        parser.print_(out, verbose)
                print >>out
        if format != "trac":
            print >>out, "Total: %s parsers" % len(self.parser_list)


class HachoirParserList(ParserList):
    _instance = None

    @classmethod
    def getInstance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        ParserList.__init__(self)
        self._load()

    def _load(self):
        """
        Load all parsers from "hachoir.parser" module.

        Return the list of loaded parsers.
        """
        # Parser list is already loaded?
        if self.parser_list:
            return self.parser_list

        todo = []
        module = __import__("hachoir_parser")
        for attrname in dir(module):
            attr = getattr(module, attrname)
            if isinstance(attr, types.ModuleType):
                todo.append(attr)

        for module in todo:
            for name in dir(module):
                attr = getattr(module, name)
                if isinstance(attr, type) \
                and issubclass(attr, HachoirParser) \
                and attr not in (Parser, HachoirParser):
                    self.add(attr)
        assert 1 <= len(self.parser_list)
        return self.parser_list

