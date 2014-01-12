# If you run this file, it will make up a random secret and then crack it
# using timing information from a string comparison function. Maybe--if it
# gets lucky. It takes a long, long time to work.

# So, the thing I need help with is statistics. The way this thing works is
# extremely stupid. Suppose you want to know which function invocation takes
# longer: comparison(secret, guess1) or comparison(secret, guess2)?

# If you can correctly determine that one of them takes longer than the
# other, then (a) you can use that to crack the secret, and (b) this is a
# unit test demonstrating that comparison() is not timing-safe.

# So how does this script do it? Extremely stupidly. First of all, you can't
# reliably measure tiny times, so to measure the time that a function takes,
# we run that function 10,000 times in a row, measure how long that took, and
# divide by 10,000 to estimate how long any one run would have taken.

# Then, we do that 100 times in a row, and take the fastest of 100 runs. (I
# also experimented with taking the mean of 100 runs instead of the fastest.)

# Then, we just say whichever comparison took longer (for its fastest run of
# 100 runs of 10,000 executions per run) is the one we think is a closer
# guess to the secret.

# Now I would *like* to think that there is some kind of statistical analysis
# more sophisticated than "take the slowest of the fastest of 100 runs of
# 10,000 executions". Such improved statistical analysis would hopefully be
# able to answer these two questions:

# 1. Are these two function calls -- comparison(secret, guess1) and
# comparison(secret, guess2) -- drawing from the same distribution or
# different? If you can answer that question, then you've answered the
# question of whether "comparison" is timing-safe or not.

# And, this would also allow the cracker to recover from a false step. If it
# incorrectly decides the the prefix of the secret is ABCX, when the real
# secret is ABCD, then after that every next step it takes will be the
# "drawing from the same distribution" kind -- any difference between ABCXQ
# and ABCXR will be just due to noise, since both are equally far from the
# correct answer, which startsw with ABCD. If it could realize that there is
# no real difference between the distributions, then it could back-track and
# recover.

# 2. Giving the ability to measure, noisily, the time taken by comparison(),
# how can you most efficiently figure out which guess takes the longest? If
# you can do that more efficiently, you can crack secrets more efficiently.

# The script takes two arguments. The first is how many symbols in the
# secret, and the second is how big the alphabet from which the symbols are
# drawn. To prove that this script can *ever* work, try passing length 5 and
# alphabet size 2. Also try editing the code to let is use sillycomp. That'll
# definitely make it work. If you can improve this script (as per the thing
# above about "needing better statistics") to the degree that it can crack a
# secret with length 32 and alphabet size 256, then that would be awesome.

# See the result of this commandline:

# $ python -c 'import time_comparisons ; time_comparisons.print_measurements()'


from pyutil import benchutil

import hashlib, random, os

from decimal import Decimal
D=Decimal

p1 = 'a'*32
p1a = 'a'*32
p2 = 'a'*31+'b' # close, but no cigar
p3 = 'b'*32 # different in the first byte

def randstr(n, alphabetsize):
    alphabet = [ chr(x) for x in range(alphabetsize) ]
    return ''.join([random.choice(alphabet) for i in range(n)])

def compare(n, f, a, b):
    for i in xrange(n):
        f(a, b)

def eqeqcomp(a, b):
    return a == b

def sillycomp(a, b):
    # This exposes a lot of information in its timing about how many leading bytes match.
    for i in range(len(a)):
        if a[i] != b[i]:
            return False
        for i in xrange(2**9):
            pass
    if len(a) == len(b):
        return True
    else:
        return False

def hashcomp(a, b):
    # Brian Warner invented this for Tahoe-LAFS. It seems like it should be very safe agaist timing leakage of any kind, because of the inclusion of a new random randkey every time. Note that exposing the value of the hash (i.e. the output of md5(randkey+secret)) is *not* a security problem. You can post that on your web site and let all attackers have it, no problem. (Provided that the value of "randkey" remains secret.)

    randkey = os.urandom(32)
    return hashlib.md5(randkey+ a).digest() == hashlib.md5(randkey+b).digest()

def xorcomp(a, b):
    # This appears to be the most popular timing-insensitive string comparison function. I'm not completely sure it is fully timing-insensitive. (There are all sorts of funny things inside Python, such as caching of integer objects < 100...)
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0

def print_measurements():
    N=10**4
    REPS=10**2

    print "all times are in nanoseconds per comparison (in scientific notation)"
    print

    for comparator in [eqeqcomp, hashcomp, xorcomp, sillycomp]:
        print "using comparator ", comparator

        # for (a, b, desc) in [(p1, p1a, 'same'), (p1, p2, 'close'), (p1, p3, 'far')]:
        trials = [(p1, p1a, 'same'), (p1, p2, 'close'), (p1, p3, 'far')]
        random.shuffle(trials)
        for (a, b, desc) in trials:
            print "comparing two strings that are %s to each other" % (desc,)

            def f(n):
                compare(n, comparator, a, b)

            benchutil.rep_bench(f, N, UNITS_PER_SECOND=10**9, MAXREPS=REPS)

            print

def try_to_crack_secret(cracker, comparator, secretlen, alphabetsize):
    secret = randstr(secretlen, alphabetsize)

    def test_guess(x):
        return comparator(secret, x)

    print "Giving cracker %s a chance to figure out the secret. Don't tell him, but the secret is %s. Whenever he makes a guess, we'll use comparator %s to decide if his guess is right ..." % (cracker, secret.encode('hex'), comparator,)

    guess = cracker(test_guess, secretlen, alphabetsize)

    print "Cracker %s guessed %r" % (cracker, guess,)
    if guess == secret:
        print "HE FIGURED IT OUT!? HOW DID HE DO THAT."
    else:
        print "HAHA. Our secret is safe."

def byte_at_a_time_cracker(test_guess, secretlen, alphabetsize):
    # If we were cleverer, we'd add some backtracking behaviour where, if we can't find any x such that ABCx stands out from the crowd as taking longer than all the other ABCy's, then we start to think that we've taken a wrong step and we go back to trying ABy's. Make sense? But we're not that clever. Once we take a step, we don't backtrack.

    print

    guess=[]

    while len(guess) < secretlen:
        best_next_byte = None
        best_next_byte_time = None

        # For each possible byte...
        for next_byte in range(alphabetsize):
            c = chr(next_byte)

            # Construct a guess with our best candidate so far...
            candidate_guess = guess[:]

            # Plus that byte...
            candidate_guess.append(c)
            s = ''.join(candidate_guess)

            # Plus random bytes...
            s += os.urandom(32 - len(s))

            # And see how long it takes the test_guess to consider it...
            def f(n):
                for i in xrange(n):
                    test_guess(s)

            times = benchutil.rep_bench(f, 10**7, MAXREPS=10**3, quiet=True)

            fastesttime = times['mean']

            print "%s..."%(c.encode('hex'),),
            if best_next_byte is None or fastesttime > best_next_byte_time:
                print "new candidate for slowest next-char: %s, took: %s" % (c.encode('hex'), fastesttime,),

                best_next_byte_time = fastesttime
                best_next_byte = c

        # Okay we've tried all possible next bytes. Our guess is this one (the one that took longest to be tested by test_guess):
        guess.append(best_next_byte)
        print "SLOWEST next-char %s! Current guess at secret: %s" % (best_next_byte.encode('hex'), ''.join(guess).encode('hex'),)

    guess = ''.join(guess)
    print "Our guess for the secret: %r" % (guess,)
    return guess

if __name__ == '__main__':
    import sys
    secretlen = int(sys.argv[1])
    alphabetsize = int(sys.argv[2])
    if alphabetsize > 256:
        raise Exception("We assume we can fit one element of the alphabet into a byte.")

    print "secretlen: %d, alphabetsize: %d" % (secretlen, alphabetsize,)

    # try_to_crack_secret(byte_at_a_time_cracker, sillycomp, secretlen, alphabetsize)
    try_to_crack_secret(byte_at_a_time_cracker, eqeqcomp, secretlen, alphabetsize)
