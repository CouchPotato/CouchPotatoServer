from pyutil import randutil
import random
from decimal import Decimal

l = []
s = None

def data_strings(N):
    assert isinstance(N, int), (N, type(N))
    del l[:]
    for i in range(N):
        l.append(repr(randutil.insecurerandstr(4)))
    global s
    s = json.dumps(l)

def data_Decimals(N):
    del l[:]
    for i in range(N):
        l.append(Decimal(str(random.randrange(0, 1000000000)))/random.randrange(1, 1000000000))
    global s
    s = jsonutil.dumps(l)

def data_floats(N):
    del l[:]
    for i in range(N):
        l.append(float(random.randrange(0, 1000000000))/random.randrange(1, 1000000000))
    global s
    s = json.dumps(l)

import json
from pyutil import jsonutil

def je(N):
    return json.dumps(l)

def ue(N):
    return jsonutil.dumps(l)

def jd(N):
    return json.loads(s)

def ud(N):
    return jsonutil.loads(s)

from pyutil import benchutil

for i in (data_strings, data_floats, data_Decimals):
    for e in (ud, ue, jd, je):
    # for e in (ue,):
        print "i: %s, e: %s" % (i, e,)
        try:
            benchutil.bench(e, initfunc=i, TOPXP=5, profile=False)
        except TypeError, e:
            print "skipping due to %s" % (e,)
benchutil.print_bench_footer()
