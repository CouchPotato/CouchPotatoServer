#  Copyright (c) 2002-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

# from the Python Standard Library
import exceptions, gc, math, operator, os, sys, types

# from the pyutil library
from assertutil import precondition
import mathutil

class Canary:
    """
    Want to get a printout when your object is garbage collected?  Then put "self.canary = Canary(self)" in your object's constructor.
    """
    def __init__(self, owner):
        self.ownerdesc = repr(owner)

    def __del__(self):
        print "Canary says that %s is gone." % self.ownerdesc

def estimate_mem_of_obj(o):
    # assumes 32-bit CPUs...
    PY_STRUCT_HEAD_LEN=4
    if hasattr(o, '__len__'):
        if isinstance(o, str):
            return PY_STRUCT_HEAD_LEN + o.__len__() * 1
        if isinstance(o, unicode):
            return PY_STRUCT_HEAD_LEN + o.__len__() * 4 # 4 depends on implementation and is approximate
        if isinstance(o, (tuple, list,)):
            return PY_STRUCT_HEAD_LEN + o.__len__() * 4
        if isinstance(o, (dict, set,)):
            return PY_STRUCT_HEAD_LEN + o.__len__() * 4 * 2 * 2 # approximate
    if isinstance(o, int):
        return PY_STRUCT_HEAD_LEN + 4
    if isinstance(o, long):
        return PY_STRUCT_HEAD_LEN + 4
        if o < 1:
            return PY_STRUCT_HEAD_LEN
        else:
            return PY_STRUCT_HEAD_LEN + math.log(o) / 5 # the 5 was empirically determined (it is approximate)
    if isinstance(o, float):
        return PY_STRUCT_HEAD_LEN + 8

    # Uh-oh...  I wonder what we are missing here...
    return PY_STRUCT_HEAD_LEN

def check_for_obj_leakage(f, *args, **kwargs):
    """
    The idea is that I am going to invoke f(), then run gc.collect(), then run
    gc.get_objects() to get a complete list of all objects in the system, then
    invoke f() a second time, then run gc.collect(), then run gc.get_objects()
    to get a list of all the objects *now* in the system.

    Then I return a tuple two things: the first element of the tuple is the
    difference between the number of objects in the second list and the number
    of objects in the first list.

    I.e., if this number is zero then you can be pretty sure there is no memory
    leak, unless f is deleting some objects and replacing them by exactly the
    same number of objects but the new objects take up more memory. If this
    number is greater than zero then you can pretty sure there is a memory
    leak, unless f is doing some memoization/caching behavior and it will
    eventually stabilize, which you can detect by running
    check_for_obj_leakage() more times and seeing if it stabilizes.

    (Actually we run f() followed by gc.collect() one time before we start in
    order to account for any static objects which are created the first time
    you run f() and then re-used after that.)

    The second element in the return value is the set of all objects which were
    present in the second list and not in the first. Some of these objects
    might be memory-leaked objects, or perhaps f deleted some objects and
    replaced them with equivalent objects, in which case these objects are not
    leaked.

    (We actually invoke gc.collect() three times in a row in case there are
    objects which get collected in the first pass that have finalizers which
    create new reference-cycled objects... "3" is a superstitious number -- we
    figure most of the time the finalizers of the things produced by the first
    round of finalizers won't themselves product another round of
    reference-cycled objects.)
    """
    f()
    gc.collect();gc.collect();gc.collect()
    f()
    gc.collect();gc.collect();gc.collect()
    r1 = gc.get_objects()
    f()
    gc.collect();gc.collect();gc.collect()
    r2 = gc.get_objects()
    d2 = dict([(id(x), x) for x in r2])

    # Now remove everything from r1, and r1 itself, from d2.
    del d2[id(r1)]
    for o in r1:
        if id(o) in d2:
            del d2[id(o)]

    return (len(r2) - len(r1) - 1, d2)

def measure_obj_leakage(f, numsamples=2**7, iterspersample=2**4, *args, **kwargs):
    """
    The idea is we are going to use count_all_objects() to see how many
    objects are in use, and keep track of that number with respect to how
    many times we've invoked f(), and return the slope of the best linear
    fit.

    @param numsamples: recommended: 2**7

    @param iterspersample: how many times f() should be invoked per sample;
                           Basically, choose iterspersample such that
                           iterspersample * numsamples *
                           how-long-it-takes-to-compute-f() is slightly less
                           than how long you are willing to wait for this
                           leak test.

    @return: the slope of the best linear fit, which can be interpreted as 'the
             approximate number of Python objects created and not destroyed
             per invocation of f()'
    """
    precondition(numsamples > 0, "numsamples is required to be positive.", numsamples)
    precondition(iterspersample > 0, "iterspersample is required to be positive.", iterspersample)

    resiters = [None]*numsamples # values: iters
    resnumobjs = [None]*numsamples # values: numobjs

    totaliters = 0
    for i in range(numsamples):
        for j in range(iterspersample):
            f(*args, **kwargs)
        totaliters = totaliters + iterspersample
        resiters[i] = totaliters
        gc.collect()
        resnumobjs[i] = count_all_objects()
        # print "totaliters: %s, numobjs: %s" % (resiters[-1], resnumobjs[-1],)

    avex = float(reduce(operator.__add__, resiters)) / len(resiters)
    avey = float(reduce(operator.__add__, resnumobjs)) / len(resnumobjs)
    sxy = reduce(operator.__add__, map(lambda a, avex=avex, avey=avey: (a[0] - avex) * (a[1] - avey), zip(resiters, resnumobjs)))
    sxx = reduce(operator.__add__, map(lambda a, avex=avex: (a - avex) ** 2, resiters))
    return sxy / sxx

def linear_fit_slope(xs, ys):
    avex = float(reduce(operator.__add__, xs)) / len(xs)
    avey = float(reduce(operator.__add__, ys)) / len(ys)
    sxy = reduce(operator.__add__, map(lambda a, avex=avex, avey=avey: (a[0] - avex) * (a[1] - avey), zip(xs, ys)))
    sxx = reduce(operator.__add__, map(lambda a, avex=avex: (a - avex) ** 2, xs))
    return sxy / sxx

def measure_ref_leakage(f, numsamples=2**7, iterspersample=2**4, *args, **kwargs):
    """
    The idea is we are going to use sys.gettotalrefcount() to see how many
    references are extant, and keep track of that number with respect to how
    many times we've invoked f(), and return the slope of the best linear
    fit.

    @param numsamples: recommended: 2**7

    @param iterspersample: how many times f() should be invoked per sample;
                           Basically, choose iterspersample such that
                           iterspersample * numsamples *
                           how-long-it-takes-to-compute-f() is slightly less
                           than how long you are willing to wait for this
                           leak test.

    @return: the slope of the best linear fit, which can be interpreted as 'the
             approximate number of Python references created and not
             nullified per invocation of f()'
    """
    precondition(numsamples > 0, "numsamples is required to be positive.", numsamples)
    precondition(iterspersample > 0, "iterspersample is required to be positive.", iterspersample)

    try:
        sys.gettotalrefcount()
    except AttributeError, le:
        raise AttributeError(le, "Probably this is not a debug build of Python, so it doesn't have a sys.gettotalrefcount function.")
    resiters = [None]*numsamples # values: iters
    resnumrefs = [None]*numsamples # values: numrefs

    totaliters = 0
    for i in range(numsamples):
        for j in range(iterspersample):
            f(*args, **kwargs)
        totaliters = totaliters + iterspersample
        resiters[i] = totaliters
        gc.collect()
        resnumrefs[i] = sys.gettotalrefcount()
        # print "totaliters: %s, numrefss: %s" % (resiters[-1], resnumrefs[-1],)

    avex = float(reduce(operator.__add__, resiters)) / len(resiters)
    avey = float(reduce(operator.__add__, resnumrefs)) / len(resnumrefs)
    sxy = reduce(operator.__add__, map(lambda a, avex=avex, avey=avey: (a[0] - avex) * (a[1] - avey), zip(resiters, resnumrefs)))
    sxx = reduce(operator.__add__, map(lambda a, avex=avex: (a - avex) ** 2, resiters))
    return sxy / sxx

class NotSupportedException(exceptions.StandardError):
    """
    Just an exception class. It is thrown by get_mem_usage if the OS does
    not support the operation.
    """
    pass

def get_mem_used():
    """
    This only works on Linux, and only if the /proc/$PID/statm output is the
    same as that in linux kernel 2.6.  Also `os.getpid()' must work.

    @return: tuple of (res, virt) used by this process
    """
    try:
        import resource
    except ImportError:
        raise NotSupportedException
    # sample output from cat /proc/$PID/statm:
    # 14317 3092 832 279 0 2108 0
    a = os.popen("cat /proc/%s/statm 2>/dev/null" % os.getpid()).read().split()
    if not a:
        raise NotSupportedException
    return (int(a[1]) * resource.getpagesize(), int(a[0]) * resource.getpagesize(),)

def get_mem_used_res():
    """
    This only works on Linux, and only if the /proc/$PID/statm output is the
    same as that in linux kernel 2.6.  Also `os.getpid()' must work.
    """
    try:
        import resource
    except ImportError:
        raise NotSupportedException
    # sample output from cat /proc/$PID/statm:
    # 14317 3092 832 279 0 2108 0
    a = os.popen("cat /proc/%s/statm" % os.getpid()).read().split()
    if not len(a) > 1:
        raise NotSupportedException
    return int(a[1]) * resource.getpagesize()

def get_mem_usage_virt_and_res():
    """
    This only works on Linux, and only if the /proc/$PID/statm output is the
    same as that in linux kernel 2.6.  Also `os.getpid()' must work.
    """
    try:
        import resource
    except ImportError:
        raise NotSupportedException
    # sample output from cat /proc/$PID/statm:
    # 14317 3092 832 279 0 2108 0
    a = os.popen("cat /proc/%s/statm" % os.getpid()).read().split()
    if not len(a) > 1:
        raise NotSupportedException
    return (int(a[0]) * resource.getpagesize(), int(a[1]) * resource.getpagesize(),)

class Measurer(object):
    def __init__(self, f, numsamples=2**7, iterspersample=2**4, *args, **kwargs):
        """
        @param f a callable; If it returns a deferred then the memory will not
            be measured and the next iteration will not be started until the
            deferred fires; else the memory will be measured and the next
            iteration started when f returns.
        """
        self.f = f
        self.numsamples = numsamples
        self.iterspersample = iterspersample
        self.args = args
        self.kwargs = kwargs
        # from twisted
        from twisted.internet import defer
        self.d = defer.Deferred()

    def when_complete(self):
        return self.d

    def  _invoke(self):
        d = self.f(*self.args, **self.kwargs)
        # from twisted
        from twisted.internet import defer
        if isinstance(d, defer.Deferred):
            d.addCallback(self._after)
        else:
            self._after(None)

    def start(self):
        self.resiters = [None]*self.numsamples # values: iters
        self.resmemusage = [None]*self.numsamples # values: memusage
        self.totaliters = 0
        self.i = 0
        self.j = 0
        self._invoke()

    def _after(self, o):
        self.j += 1
        if self.j < self.iterspersample:
            self._invoke()
            return

        if self.i < self.numsamples:
            self.j = 0
            self.i += 1
            self.totaliters += self.iterspersample
            self.resiters[self.i] = self.totaliters
            self.resmemusage[self.i]  = get_mem_used_res()
            self._invoke()
            return

        self.d.callback(mathutil.linear_fit_slope(zip(self.resiters, self.resmemusage)))

def measure_mem_leakage(f, numsamples=2**7, iterspersample=2**4, *args, **kwargs):
    """
    This does the same thing as measure_obj_leakage() but instead of using
    count_all_objects() it uses get_mem_usage(), which is currently
    implemented for Linux and barely implemented for Mac OS X.

    @param numsamples: recommended: 2**7

    @param iterspersample: how many times `f()' should be invoked per sample;
                           Basically, choose `iterspersample' such that
                           (iterspersample * numsamples *
                           how-long-it-takes-to-compute-`f()') is slightly
                           less than how long you are willing to wait for
                           this leak test.

    @return: the slope of the best linear fit, which can be interpreted as
             'the approximate number of system bytes allocated and not freed
             per invocation of f()'
    """
    precondition(numsamples > 0, "numsamples is required to be positive.", numsamples)
    precondition(iterspersample > 0, "iterspersample is required to be positive.", iterspersample)

    resiters = [None]*numsamples # values: iters
    resmemusage = [None]*numsamples # values: memusage

    totaliters = 0
    for i in range(numsamples):
        for j in range(iterspersample):
            f(*args, **kwargs)
        totaliters = totaliters + iterspersample
        resiters[i] = totaliters
        gc.collect()
        resmemusage[i] = get_mem_used_res()
        # print "totaliters: %s, numobjs: %s" % (resiters[-1], resmemusage[-1],)

    avex = float(reduce(operator.__add__, resiters)) / len(resiters)
    avey = float(reduce(operator.__add__, resmemusage)) / len(resmemusage)
    sxy = reduce(operator.__add__, map(lambda a, avex=avex, avey=avey: (a[0] - avex) * (a[1] - avey), zip(resiters, resmemusage)))
    sxx = reduce(operator.__add__, map(lambda a, avex=avex: (a - avex) ** 2, resiters))
    if sxx == 0:
        return None
    return sxy / sxx

def describe_object(o, FunctionType=types.FunctionType, MethodType=types.MethodType, InstanceType=types.InstanceType):
    """
    For human analysis, when humans are attempting to understand where all the
    memory is going.  Argument o is an object, return value is a string
    describing the object.
    """
    sl = []
    if isinstance(o, FunctionType):
        try:
            sl.append("<type 'function' %s>" % str(o.func_name))
        except:
            pass
    elif isinstance(o, MethodType):
        try:
            sl.append("<type 'method' %s>" % str(o.im_func.func_name))
        except:
            pass
    elif isinstance(o, InstanceType):
        try:
            sl.append("<type 'instance' %s>" % str(o.__class__.__name__))
        except:
            pass
    else:
        sl.append(str(type(o)))

    try:
        sl.append(str(len(o)))
    except:
        pass
    return ''.join(sl)

import dictutil
def describe_object_with_dict_details(o):
    sl = []
    sl.append(str(type(o)))
    if isinstance(o, types.FunctionType):
        try:
            sl.append(str(o.func_name))
        except:
            pass
    elif isinstance(o, types.MethodType):
        try:
            sl.append(str(o.im_func.func_name))
        except:
            pass
    try:
        sl.append(str(len(o)))
    except:
        pass
    if isinstance(o, dict) and o:
        sl.append('-')
        nd = dictutil.NumDict()
        for k, v in o.iteritems():
            nd.inc((describe_object(k), describe_object(v),))
        k, v = nd.item_with_largest_value()
        sl.append("-")
        iterator = o.iteritems()
        k,v =  iterator.next()
        sl.append(describe_object(k))
        sl.append(":")
        sl.append(describe_object(v))
    return ''.join(sl)

def describe_dict(o):
    sl = ['<dict']
    l = len(o)
    sl.append(str(l))
    if l:
        sl.append("-")
        iterator = o.iteritems()
        firstitem=True
        try:
            while True:
                if firstitem:
                    firstitem = False
                else:
                    sl.append(", ")
                k,v =  iterator.next()
                sl.append(describe_object(k))
                sl.append(": ")
                sl.append(describe_object(v))
        except StopIteration:
            pass
    sl.append('>')
    return ''.join(sl)

def count_all_objects():
    ids = set()
    ls = locals()
    import inspect
    cf = inspect.currentframe()
    for o in gc.get_objects():
        if o is ids or o is ls or o is cf:
            continue
        if not id(o) in ids:
            ids.add(id(o))
        for so in gc.get_referents(o):
            if not id(so) in ids:
                ids.add(id(so))
    return len(ids)

def visit_all_objects(f):
    """
    Brian and I *think* that this gets all objects.  This is predicated on the
    assumption that every object either participates in gc, or is at most one
    hop from an object that participates in gc.  This was Brian's clever idea.
    """
    ids = set()
    ls = locals()
    import inspect
    cf = inspect.currentframe()
    for o in gc.get_objects():
        if o is ids or o is ls or o is cf:
            continue
        if not id(o) in ids:
            ids.add(id(o))
            f(o)
        for so in gc.get_referents(o):
            if not id(so) in ids:
                ids.add(id(so))
                f(so)

def get_all_objects():
    objs = []
    def addit(o):
        objs.append(o)
    visit_all_objects(addit)
    return objs

def describe_all_objects():
    import dictutil
    d = dictutil.NumDict()
    for o in get_all_objects():
        d.inc(describe_object(o))
    return d

def dump_description_of_object(o, f):
    f.write("%x" % (id(o),))
    f.write("-")
    f.write(describe_object(o))
    f.write("\n")

def dump_description_of_object_refs(o, f):
    # This holds the ids of all referents that we've already dumped.
    dumped = set()

    # First, any __dict__ items
    try:
        itemsiter = o.__dict__.iteritems()
    except:
        pass
    else:
        for k, v in itemsiter:
            try:
                idr = id(v)
                if idr not in dumped:
                    dumped.add(idr)
                    f.write("%d:"%len(k))
                    f.write(k)
                    f.write(",")
                    f.write("%0x,"%idr)
            except:
                pass

    # Then anything else that gc.get_referents() returns.
    for r in gc.get_referents(o):
        idr = id(r)
        if idr not in dumped:
            dumped.add(idr)
            f.write("0:,%0x,"%idr)

def dump_descriptions_of_all_objects(f):
    ids = set()
    ls = locals()
    for o in gc.get_objects():
        if o is f or o is ids or o is ls:
            continue
        if not id(o) in ids:
            ids.add(id(o))
            dump_description_of_object(o, f)
        for so in gc.get_referents(o):
            if o is f or o is ids or o is ls:
                continue
            if not id(so) in ids:
                ids.add(id(so))
                dump_description_of_object(so, f)
    ls = None # break reference cycle
    return len(ids)  

def dump_description_of_object_with_refs(o, f):
    f.write("%0x" % (id(o),))
    f.write("-")
    desc = describe_object(o)
    f.write("%d:"%len(desc))
    f.write(desc)
    f.write(",")

    dump_description_of_object_refs(o, f)
    f.write("\n")

def dump_descriptions_of_all_objects_with_refs(f):
    ids = set()
    ls = locals()
    for o in gc.get_objects():
        if o is f or o is ids or o is ls:
            continue
        if not id(o) in ids:
            ids.add(id(o))
            dump_description_of_object_with_refs(o, f)
        for so in gc.get_referents(o):
            if o is f or o is ids or o is ls:
                continue
            if not id(so) in ids:
                ids.add(id(so))
                dump_description_of_object_with_refs(so, f)
    ls = None # break reference cycle
    return len(ids)  

import re
NRE = re.compile("[1-9][0-9]*$")
def undump_descriptions_of_all_objects(inf):
    d = {}
    for l in inf:
        dash=l.find('-')
        if dash == -1:
            raise l
        mo = NRE.search(l) 
        if mo:
            typstr = l[dash+1:mo.start(0)]
            num=int(mo.group(0))
            if str(num) != mo.group(0):
                raise mo.group(0)
        else:
            typstr = l[dash+1:]
            num = None
        d[l[:dash]] = (typstr, num,)
    return d
