#!/usr/bin/env python
"""\
Test time_format.py
"""

import os, time, unittest

from pyutil import time_format, increasing_timer

class TimeUtilTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_iso8601_utc_time(self, timer=increasing_timer.timer):
        ts1 = time_format.iso_utc(timer.time() - 20)
        ts2 = time_format.iso_utc()
        assert ts1 < ts2, "failed: %s < %s" % (ts1, ts2)
        ts3 = time_format.iso_utc(timer.time() + 20)
        assert ts2 < ts3, "failed: %s < %s" % (ts2, ts3)

    def test_iso_utc_time_to_localseconds(self, timer=increasing_timer.timer):
        # test three times of the year so that a DST problem would hopefully be triggered
        t1 = int(timer.time() - 365*3600/3)
        iso_utc_t1 = time_format.iso_utc(t1)
        t1_2 = time_format.iso_utc_time_to_seconds(iso_utc_t1)
        assert t1 == t1_2, (t1, t1_2)
        t1 = int(timer.time() - (365*3600*2/3))
        iso_utc_t1 = time_format.iso_utc(t1)
        t1_2 = time_format.iso_utc_time_to_seconds(iso_utc_t1)
        self.failUnlessEqual(t1, t1_2)
        t1 = int(timer.time())
        iso_utc_t1 = time_format.iso_utc(t1)
        t1_2 = time_format.iso_utc_time_to_seconds(iso_utc_t1)
        self.failUnlessEqual(t1, t1_2)

    def test_epoch(self):
        return self._help_test_epoch()

    def test_epoch_in_London(self):
        # Europe/London is a particularly troublesome timezone.  Nowadays, its
        # offset from GMT is 0.  But in 1970, its offset from GMT was 1.
        # (Apparently in 1970 Britain had redefined standard time to be GMT+1
        # and stayed in standard time all year round, whereas today
        # Europe/London standard time is GMT and Europe/London Daylight
        # Savings Time is GMT+1.)  The current implementation of
        # time_format.iso_utc_time_to_seconds() breaks if the timezone is
        # Europe/London.  (As soon as this unit test is done then I'll change
        # that implementation to something that works even in this case...)
        origtz = os.environ.get('TZ')
        os.environ['TZ'] = "Europe/London"
        if hasattr(time, 'tzset'):
            time.tzset()
        try:
            return self._help_test_epoch()
        finally:
            if origtz is None:
                del os.environ['TZ']
            else:
                os.environ['TZ'] = origtz
            if hasattr(time, 'tzset'):
                time.tzset()

    def _help_test_epoch(self):
        origtzname = time.tzname
        s = time_format.iso_utc_time_to_seconds("1970-01-01T00:00:01Z")
        self.failUnlessEqual(s, 1.0)
        s = time_format.iso_utc_time_to_seconds("1970-01-01_00:00:01Z")
        self.failUnlessEqual(s, 1.0)
        s = time_format.iso_utc_time_to_seconds("1970-01-01 00:00:01Z")
        self.failUnlessEqual(s, 1.0)

        self.failUnlessEqual(time_format.iso_utc(1.0), "1970-01-01 00:00:01Z")
        self.failUnlessEqual(time_format.iso_utc(1.0, sep="_"),
                             "1970-01-01_00:00:01Z")

        now = time.time()
        isostr = time_format.iso_utc(now)
        timestamp = time_format.iso_utc_time_to_seconds(isostr)
        self.failUnlessEqual(int(timestamp), int(now))

        def my_time():
            return 1.0
        self.failUnlessEqual(time_format.iso_utc(t=my_time),
                             "1970-01-01 00:00:01Z")
        self.failUnlessRaises(ValueError,
                                  time_format.iso_utc_time_to_seconds,
                                  "invalid timestring")
        s = time_format.iso_utc_time_to_seconds("1970-01-01 00:00:01.500Z")
        self.failUnlessEqual(s, 1.5)

        # Look for daylight-savings-related errors.
        thatmomentinmarch = time_format.iso_utc_time_to_seconds("2009-03-20 21:49:02.226536Z")
        self.failUnlessEqual(thatmomentinmarch, 1237585742.226536)
        self.failUnlessEqual(origtzname, time.tzname)
