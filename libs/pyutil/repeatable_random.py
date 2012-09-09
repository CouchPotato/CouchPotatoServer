"""
If you execute force_repeatability() then the following things are changed in the runtime:

1.  random.random() and its sibling functions, and random.Random.seed() in the random module are seeded with a known seed so that they will return the same sequence on each run.
2.  os.urandom() is replaced by a fake urandom that returns a pseudorandom sequence.
3.  time.time() is replaced by a fake time that returns an incrementing number.  (Original time.time is available as time.realtime.)

Which seed will be used?

If the environment variable REPEATABLE_RANDOMNESS_SEED is set, then it will use that.  Else, it will use the current real time.  In either case it logs the seed that it used.

Caveats:

1.  If some code has acquired a random.Random object before force_repeatability() is executed, then that Random object will produce non-reproducible results.  For example, the tempfile module in the Python Standard Library does this.
2.  Likewise if some code called time.time() before force_repeatability() was called, then it will have gotten a real time stamp.  For example, trial does this.  (Then it later subtracts that real timestamp from a faketime timestamp to calculate elapsed time, resulting in a large negative elapsed time.)
3.  Fake urandom has an added constraint for performance reasons -- you can't ask it for more than 64 bytes of randomness at a time.  (I couldn't figure out how to generate large fake random strings efficiently.)
"""

import os, random, time
if not hasattr(time, "realtime"):
    time.realtime = time.time
if not hasattr(os, "realurandom"):
    os.realurandom = os.urandom
if not hasattr(random, "realseed"):
    random.realseed = random.seed

tdelta = 0
seeded = False
def force_repeatability():
    now = 1043659734.0
    def faketime():
        global tdelta
        tdelta += 1
        return now + tdelta
    time.faketime = faketime
    time.time = faketime

    from idlib import i2b
    def fakeurandom(n):
        if n > 64:
            raise ("Can't produce more than 64 bytes of pseudorandomness efficiently.")
        elif n == 0:
            return ''
        else:
            z = i2b(random.getrandbits(n*8))
        x = z + "0" * (n-len(z))
        assert len(x) == n
        return x
    os.fakeurandom = fakeurandom
    os.urandom = fakeurandom

    global seeded
    if not seeded:
        SEED = os.environ.get('REPEATABLE_RANDOMNESS_SEED', None)

        if SEED is None:
            # Generate a seed which is integral and fairly short (to ease cut-and-paste, writing it down, etc.).
            t = time.realtime()
            subsec = t % 1
            t += (subsec * 1000000)
            t %= 1000000
            SEED = long(t)
        import sys
        sys.stdout.write("REPEATABLE_RANDOMNESS_SEED: %s\n" % SEED) ; sys.stdout.flush()
        sys.stdout.write("In order to reproduce this run of the code, set the environment variable \"REPEATABLE_RANDOMNESS_SEED\" to %s before executing.\n" % SEED) ; sys.stdout.flush()
        random.seed(SEED)

        def seed_which_refuses(a):
            sys.stdout.write("I refuse to reseed to %s.  Go away!\n" % (a,)) ; sys.stdout.flush()
            return
        random.realseed = random.seed
        random.seed = seed_which_refuses
        seeded = True

    import setutil
    setutil.RandomSet.DETERMINISTIC = True

def restore_real_clock():
    time.time = time.realtime

def restore_real_urandom():
    os.urandom = os.realurandom

def restore_real_seed():
    random.seed = random.realseed

def restore_non_repeatability():
    restore_real_seed()
    restore_real_urandom()
    restore_real_clock()
