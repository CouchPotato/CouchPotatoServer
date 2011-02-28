from hachoir_core.tools import humanDurationNanosec
from hachoir_core.i18n import _
from math import floor
from time import time

class BenchmarkError(Exception):
    """
    Error during benchmark, use str(err) to format it as string.
    """
    def __init__(self, message):
        Exception.__init__(self,
            "Benchmark internal error: %s" % message)

class BenchmarkStat:
    """
    Benchmark statistics. This class automatically computes minimum value,
    maximum value and sum of all values.

    Methods:
    - append(value): append a value
    - getMin(): minimum value
    - getMax(): maximum value
    - getSum(): sum of all values
    - __len__(): get number of elements
    - __nonzero__(): isn't empty?
    """
    def __init__(self):
        self._values = []

    def append(self, value):
        self._values.append(value)
        try:
            self._min = min(self._min, value)
            self._max = max(self._max, value)
            self._sum += value
        except AttributeError:
            self._min = value
            self._max = value
            self._sum = value

    def __len__(self):
        return len(self._values)

    def __nonzero__(self):
        return bool(self._values)

    def getMin(self):
        return self._min

    def getMax(self):
        return self._max

    def getSum(self):
        return self._sum

class Benchmark:
    def __init__(self, max_time=5.0,
    min_count=5, max_count=None, progress_time=1.0):
        """
        Constructor:
        - max_time: Maximum wanted duration of the whole benchmark
          (default: 5 seconds, minimum: 1 second).
        - min_count: Minimum number of function calls to get good statistics
          (defaut: 5, minimum: 1).
        - progress_time: Time between each "progress" message
          (default: 1 second, minimum: 250 ms).
        - max_count: Maximum number of function calls (default: no limit).
        - verbose: Is verbose? (default: False)
        - disable_gc: Disable garbage collector? (default: False)
        """
        self.max_time = max(max_time, 1.0)
        self.min_count = max(min_count, 1)
        self.max_count = max_count
        self.progress_time = max(progress_time, 0.25)
        self.verbose = False
        self.disable_gc = False

    def formatTime(self, value):
        """
        Format a time delta to string: use humanDurationNanosec()
        """
        return humanDurationNanosec(value * 1000000000)

    def displayStat(self, stat):
        """
        Display statistics to stdout:
        - best time (minimum)
        - average time (arithmetic average)
        - worst time (maximum)
        - total time (sum)

        Use arithmetic avertage instead of geometric average because
        geometric fails if any value is zero (returns zero) and also
        because floating point multiplication lose precision with many
        values.
        """
        average = stat.getSum() / len(stat)
        values = (stat.getMin(), average, stat.getMax(), stat.getSum())
        values = tuple(self.formatTime(value) for value in values)
        print _("Benchmark: best=%s  average=%s  worst=%s  total=%s") \
            % values

    def _runOnce(self, func, args, kw):
        before = time()
        func(*args, **kw)
        after = time()
        return after - before

    def _run(self, func, args, kw):
        """
        Call func(*args, **kw) as many times as needed to get
        good statistics. Algorithm:
        - call the function once
        - compute needed number of calls
        - and then call function N times

        To compute number of calls, parameters are:
        - time of first function call
        - minimum number of calls (min_count attribute)
        - maximum test time (max_time attribute)

        Notice: The function will approximate number of calls.
        """
        # First call of the benchmark
        stat = BenchmarkStat()
        diff = self._runOnce(func, args, kw)
        best = diff
        stat.append(diff)
        total_time = diff

        # Compute needed number of calls
        count = int(floor(self.max_time / diff))
        count = max(count, self.min_count)
        if self.max_count:
            count = min(count, self.max_count)

        # Not other call? Just exit
        if count == 1:
            return stat
        estimate = diff * count
        if self.verbose:
            print _("Run benchmark: %s calls (estimate: %s)") \
                % (count, self.formatTime(estimate))

        display_progress = self.verbose and (1.0 <= estimate)
        total_count = 1
        while total_count < count:
            # Run benchmark and display each result
            if display_progress:
                print _("Result %s/%s: %s  (best: %s)") % \
                    (total_count, count,
                    self.formatTime(diff), self.formatTime(best))
            part = count - total_count

            # Will takes more than one second?
            average = total_time / total_count
            if self.progress_time < part * average:
                part = max( int(self.progress_time / average), 1)
            for index in xrange(part):
                diff = self._runOnce(func, args, kw)
                stat.append(diff)
                total_time += diff
                best = min(diff, best)
            total_count += part
        if display_progress:
            print _("Result %s/%s: %s  (best: %s)") % \
                (count, count,
                self.formatTime(diff), self.formatTime(best))
        return stat

    def validateStat(self, stat):
        """
        Check statistics and raise a BenchmarkError if they are invalid.
        Example of tests: reject empty stat, reject stat with only nul values.
        """
        if not stat:
            raise BenchmarkError("empty statistics")
        if not stat.getSum():
            raise BenchmarkError("nul statistics")

    def run(self, func, *args, **kw):
        """
        Run function func(*args, **kw), validate statistics,
        and display the result on stdout.

        Disable garbage collector if asked too.
        """

        # Disable garbarge collector is needed and if it does exist
        # (Jython 2.2 don't have it for example)
        if self.disable_gc:
            try:
                import gc
            except ImportError:
                self.disable_gc = False
        if self.disable_gc:
            gc_enabled = gc.isenabled()
            gc.disable()
        else:
            gc_enabled = False

        # Run the benchmark
        stat = self._run(func, args, kw)
        if gc_enabled:
            gc.enable()

        # Validate and display stats
        self.validateStat(stat)
        self.displayStat(stat)

