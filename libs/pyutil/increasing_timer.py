#  Copyright (c) 2001 Autonomous Zone Industries
#  Copyright (c) 2002-2009 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

"""
This module was invented when it was discovered that time.time() can return
decreasing answers, which was causing scheduled tasks to get executed out of
order.  See python bug report `[ #447945 ] time.time() is not
non-decreasing',
http://sourceforge.net/tracker/index.php?func=detail&aid=447945&group_id=5470&atid=105470
http://mail.python.org/pipermail/python-list/2001-August/thread.html#58296

After posting that bug report, I figured out that this isn't really a bug,
but a misunderstanding about the semantics of gettimeofday().  gettimeofday()
relies on the hardware clock, which is supposed to reflect the "real" time
i.e. the position and orientation of our planet with regard to our sun.  But
the hardware clock gets adjusted, either for skew (because hardware clocks
always run a little faster or a little slower than they ought), or in order to
sync up with another clock e.g. through NTP.  So it isn't really a bug in the
underlying platform (except perhaps a bug in the lack of a prominent warning
in the documentation), but if you depend on a monotonically increasing
timestamps, you need to use IncreasingTimer.time() instead of the Python
standard library's time.time().  --Zooko 2001-08-04 
"""

import time as standardtime

# Here is a global reference to an IncreasingTimer.
# This singleton global IncreasingTimer instance gets created at module load time.
timer = None

class IncreasingTimer:
    def __init__(self, inittime=None):
        """
        @param inittime starting time (in seconds) or None in which case it
        will be initialized to standardtime.time()
        """
        if inittime is None:
            inittime = standardtime.time() 
        self.lasttime = inittime # This stores the most recent answer that we returned from time().
        self.delta = 0 # We add this to the result from the underlying standardtime.time().

        # How big of an increment do we need to add in order to make the new float greater than the old float?
        trye = 1.0
        while (self.lasttime + trye) > self.lasttime:
            olde = trye
            trye = trye / 2.0
        self._EPSILON = olde

    def time(self):
        """
        This returns the current time as a float, with as much precision as
        the underlying Python interpreter can muster.  In addition, successive
        calls to time() always return bigger numbers.  (standardtime.time()
        can sometimes return the same or even a *smaller* number!)

        On the other hand, calling time() is a bit slower than calling
        standardtime.time(), so you might want to avoid it inside tight loops
        and deal with decreasing or identical answers yourself.

        Now by definition you cannot "reset" this clock to an earlier state.
        This means that if you start a Python interpreter and instantiate an
        IncreasingTimer, and then you subsequently realize that your
        computer's clock was set to next year, and you set it back to the
        correct year, that subsequent calls to standardtime.time() will return
        a number indicating this year and IncreasingTimer.time() will continue
        to return a number indicating next year.  Therefore, you should use
        the answers from IncreasingTimer.time() in such a way that the only
        things you depend on are correctness in the relative *order* of two
        times, (and, with the following caveat, the relative *difference*
        between two times as well), not the global "correctness" of the times
        with respect to the rest of the world. 

        The caveat is that if the underlying answers from standardtime.time()
        jump *forward*, then this *does* distort the relative difference
        between two answers from IncreasingTimer.time().  What
        IncreasingTimer.time() does is if the underlying clock goes
        *backwards*, then IncreasingTimer.time() still returns successively
        higher numbers.  Then if the underlying clock jumps *forwards*,
        IncreasingTimer.time() also jumps forward the same amount. A weird
        consequence of this is that if you were to set your system clock to
        point to 10 years ago, and call:

        t1 = increasingtimer.time()

        and then set your system clock back to the present, and call:

        t2 = increasingtimer.time()

        , then there would be a 10-year difference between t2 and t1.

        In practice, adjustments to the underlying system time are rarely that
        drastic, and for some systems (e.g. Mnet's DoQ, for which this module
        was invented) it doesn't matter anyway if time jumps forward.

        Another note: Brian Warner has pointed out that there is another
        caveat, which is due to there being a delay between successive calls
        to IncreasingTimer.time().  When the underlying clock jumps backward,
        then events which were scheduled before the jump and scheduled to go
        off after the jump may be delayed by at most d, where d is the delay
        between the two successive calls to IncreasingTimer which spanned the
        jump.

        @singlethreaded You must guarantee that you never have more than one
            thread in this function at a time.
        """
        t = standardtime.time() + self.delta
        lasttime = self.lasttime

        if t <= lasttime:
            self.delta = self.delta + (lasttime - t) + self._EPSILON
            t = lasttime + self._EPSILON

        # TODO: If you were sure that you could generate a bigger float in one
        # pass, you could change this `while' to an `if' and optimize out a
        # test.
        while t <= lasttime:
            # We can get into here only if self._EPSILON is too small to make
            # # the time float "tick over" to a new higher value.  So we
            # (permanently) # double self._EPSILON.
            # TODO: Is doubling epsilon the best way to quickly get a
            # minimally bigger float?
            self._EPSILON = self._EPSILON * 2.0

            # Delta, having smaller magnitude than t, can be incremented by
            # more than t was incremented.  (Up to the old epsilon more.)
            # That's OK.
            self.delta = self.delta + self._EPSILON
            t = t + self._EPSILON

        self.lasttime = t
        return t

# create the global IncreasingTimer instance and `time' function
timer = IncreasingTimer()
time = timer.time
