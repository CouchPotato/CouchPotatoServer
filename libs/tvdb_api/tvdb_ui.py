#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

"""Contains included user interfaces for Tvdb show selection.

A UI is a callback. A class, it's __init__ function takes two arguments:

- config, which is the Tvdb config dict, setup in tvdb_api.py
- log, which is Tvdb's logger instance (which uses the logging module). You can
call log.info() log.warning() etc

It must have a method "selectSeries", this is passed a list of dicts, each dict
contains the the keys "name" (human readable show name), and "sid" (the shows
ID as on thetvdb.com). For example:

[{'name': u'Lost', 'sid': u'73739'},
 {'name': u'Lost Universe', 'sid': u'73181'}]

The "selectSeries" method must return the appropriate dict, or it can raise
tvdb_userabort (if the selection is aborted), tvdb_shownotfound (if the show
cannot be found).

A simple example callback, which returns a random series:

>>> import random
>>> from tvdb_ui import BaseUI
>>> class RandomUI(BaseUI):
...    def selectSeries(self, allSeries):
...            import random
...            return random.choice(allSeries)

Then to use it..

>>> from tvdb_api import Tvdb
>>> t = Tvdb(custom_ui = RandomUI)
>>> random_matching_series = t['Lost']
>>> type(random_matching_series)
<class 'tvdb_api.Show'>
"""

__author__ = "dbr/Ben"
__version__ = "1.8.2"

import logging
import warnings

from tvdb_exceptions import tvdb_userabort

def log():
    return logging.getLogger(__name__)

class BaseUI:
    """Default non-interactive UI, which auto-selects first results
    """
    def __init__(self, config, log = None):
        self.config = config
        if log is not None:
            warnings.warn("the UI's log parameter is deprecated, instead use\n"
                "use import logging; logging.getLogger('ui').info('blah')\n"
                "The self.log attribute will be removed in the next version")
            self.log = logging.getLogger(__name__)

    def selectSeries(self, allSeries):
        return allSeries[0]


class ConsoleUI(BaseUI):
    """Interactively allows the user to select a show from a console based UI
    """

    def _displaySeries(self, allSeries, limit = 6):
        """Helper function, lists series with corresponding ID
        """
        if limit is not None:
            toshow = allSeries[:limit]
        else:
            toshow = allSeries

        print "TVDB Search Results:"
        for i, cshow in enumerate(toshow):
            i_show = i + 1 # Start at more human readable number 1 (not 0)
            log().debug('Showing allSeries[%s], series %s)' % (i_show, allSeries[i]['seriesname']))
            if i == 0:
                extra = " (default)"
            else:
                extra = ""

            print "%s -> %s [%s] # http://thetvdb.com/?tab=series&id=%s&lid=%s%s" % (
                i_show,
                cshow['seriesname'].encode("UTF-8", "ignore"),
                cshow['language'].encode("UTF-8", "ignore"),
                str(cshow['id']),
                cshow['lid'],
                extra
            )

    def selectSeries(self, allSeries):
        self._displaySeries(allSeries)

        if len(allSeries) == 1:
            # Single result, return it!
            print "Automatically selecting only result"
            return allSeries[0]

        if self.config['select_first'] is True:
            print "Automatically returning first search result"
            return allSeries[0]

        while True: # return breaks this loop
            try:
                print "Enter choice (first number, return for default, 'all', ? for help):"
                ans = raw_input()
            except KeyboardInterrupt:
                raise tvdb_userabort("User aborted (^c keyboard interupt)")
            except EOFError:
                raise tvdb_userabort("User aborted (EOF received)")

            log().debug('Got choice of: %s' % (ans))
            try:
                selected_id = int(ans) - 1 # The human entered 1 as first result, not zero
            except ValueError: # Input was not number
                if len(ans.strip()) == 0:
                    # Default option
                    log().debug('Default option, returning first series')
                    return allSeries[0]
                if ans == "q":
                    log().debug('Got quit command (q)')
                    raise tvdb_userabort("User aborted ('q' quit command)")
                elif ans == "?":
                    print "## Help"
                    print "# Enter the number that corresponds to the correct show."
                    print "# a - display all results"
                    print "# all - display all results"
                    print "# ? - this help"
                    print "# q - abort tvnamer"
                    print "# Press return with no input to select first result"
                elif ans.lower() in ["a", "all"]:
                    self._displaySeries(allSeries, limit = None)
                else:
                    log().debug('Unknown keypress %s' % (ans))
            else:
                log().debug('Trying to return ID: %d' % (selected_id))
                try:
                    return allSeries[selected_id]
                except IndexError:
                    log().debug('Invalid show number entered!')
                    print "Invalid number (%s) selected!"
                    self._displaySeries(allSeries)

