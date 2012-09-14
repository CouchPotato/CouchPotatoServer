# Copyright (c) 2005-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

"""
A few commonly needed functions.
"""

import math

def div_ceil(n, d):
    """
    The smallest integer k such that k*d >= n.
    """
    return (n/d) + (n%d != 0)

def next_multiple(n, k):
    """
    The smallest multiple of k which is >= n.  Note that if n is 0 then the
    answer is 0.
    """
    return div_ceil(n, k) * k

def pad_size(n, k):
    """
    The smallest number that has to be added to n to equal a multiple of k.
    """
    if n%k:
        return k - n%k
    else:
        return 0

def is_power_of_k(n, k):
    return k**int(math.log(n, k) + 0.5) == n

def next_power_of_k(n, k):
    p = 1
    while p < n:
        p *= k
    return p

def ave(l):
    return sum(l) / len(l)

def log_ceil(n, b):
    """
    The smallest integer k such that b^k >= n.

    log_ceil(n, 2) is the number of bits needed to store any of n values, e.g.
    the number of bits needed to store any of 128 possible values is 7.
    """
    p = 1
    k = 0
    while p < n:
        p *= b
        k += 1
    return k

def log_floor(n, b):
    """
    The largest integer k such that b^k <= n.
    """
    p = 1
    k = 0
    while p <= n:
        p *= b
        k += 1
    return k - 1

def linear_fit_slope(ps):
    """
    Single-independent-variable linear regression -- least squares method.

    At least, I *think* this function computes that answer.  I no longer
    remember where I learned this trick and at the moment I can't prove to 
    myself that this is correct.

    @param ps a sequence of tuples of (x, y)
    """
    avex = ave([x for (x, y) in ps])
    avey = ave([y for (x, y) in ps])
    sxy = sum([ (x - avex) * (y - avey) for (x, y) in ps ])
    sxx = sum([ (x - avex) ** 2 for (x, y) in ps ])
    if sxx == 0:
        return None
    return sxy / sxx

def permute(l):
    """
    Return all possible permutations of l.

    @type l: sequence
    @rtype a set of sequences
    """
    if len(l) == 1:
        return [l,]

    res = []
    for i in range(len(l)):
        l2 = list(l[:])
        x = l2.pop(i)
        for l3 in permute(l2):
            l3.append(x)
            res.append(l3)

    return res

