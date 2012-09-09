from pyutil import benchutil

import hashlib, random, os

from decimal import Decimal
D=Decimal

p1 = 'a'*32
p1a = 'a'*32
p2 = 'a'*31+'b' # close, but no cigar
p3 = 'b'*32 # different in the first byte

def compare(n, f, a, b):
    for i in xrange(n):
        f(a, b)

def eqeqcomp(a, b):
    return a == b

def hashcomp(a, b):
    salt = os.urandom(32)
    return hashlib.md5(salt+ a).digest() == hashlib.md5(salt+b).digest()

N=10**4
REPS=10**2

print "all times are in nanoseconds per comparison (scientific notation)"
print

for comparator in [eqeqcomp, hashcomp]:
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
