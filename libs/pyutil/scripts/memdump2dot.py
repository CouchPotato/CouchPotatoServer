#!/usr/bin/env python

import bindann
bindann.install_exception_handler()

import sys

inf = open(sys.argv[1], "r")

outf = open(sys.argv[1]+".dot", "w")
outf.write("digraph %s {\n" % sys.argv[1].replace(".",""))

def parse_netstring(l, i):
    try:
        j = l.find(':', i)
        if j == -1:
            return (None, len(l),)
        lenval = int(l[i:j])
        val = l[j+1:j+1+lenval]
        # skip the comma
        assert l[j+1+lenval] == ","
        return (val, j+1+lenval+1,)
    except Exception, le:
        le.args = tuple(le.args + (l, i,))
        raise

def parse_ref(l, i):
    (attrname, i,) = parse_netstring(l, i)
    j = l.find(",", i)
    assert j != -1
    objid = l[i:j]
    return (objid, attrname, j+1,)

def parse_memdump_line(l):
    result = []

    i = l.find('-')
    objid = l[:i]
    (objdesc, i,) = parse_netstring(l, i+1)

    result.append((objid, objdesc,))

    while i != -1 and i < len(l):
        (objid, attrname, i,) = parse_ref(l, i)
        result.append((objid, attrname,))

    return result

for l in inf:
    if l[-1] != "\n":
        raise "waht the HECK? %r" % l
    res = parse_memdump_line(l.strip())
    # declare the node
    outf.write("\"%s\" [label=\"%s\"];\n" % (res[0][0], res[0][1],))

    # declare all the edges
    for edge in res[1:]:
        if edge[1]:
            # a named edge
            outf.write("\"%s\" -> \"%s\" [style=bold, label=\"%s\"];\n" % (res[0][0], edge[0], edge[1],))
        else:
            # an anonymous edge
            outf.write("\"%s\" -> \"%s\";\n" % (res[0][0], edge[0]))

outf.write("}")
