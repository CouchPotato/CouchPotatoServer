"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Dann Martens (TOMOTON).
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ET
import base64
import logging
import time
import sys

if sys.version_info > (3, 0):
    unicode = str

log = logging.getLogger(__name__)

_namespace = 'jabber:iq:rpc'

def fault2xml(fault):
    value = dict()
    value['faultCode'] = fault['code']
    value['faultString'] = fault['string']
    fault = ET.Element("fault", {'xmlns': _namespace})
    fault.append(_py2xml((value)))
    return fault

def xml2fault(params):
    vals = []
    for value in params.findall('{%s}value' % _namespace):
        vals.append(_xml2py(value))
    fault = dict()
    fault['code'] = vals[0]['faultCode']
    fault['string'] = vals[0]['faultString']
    return fault

def py2xml(*args):
    params = ET.Element("{%s}params" % _namespace)
    for x in args:
        param = ET.Element("{%s}param" % _namespace)
        param.append(_py2xml(x))
        params.append(param) #<params><param>...
    return params

def _py2xml(*args):
    for x in args:
        val = ET.Element("{%s}value" % _namespace)
        if x is None:
            nil = ET.Element("{%s}nil" % _namespace)
            val.append(nil)
        elif type(x) is int:
            i4 = ET.Element("{%s}i4" % _namespace)
            i4.text = str(x)
            val.append(i4)
        elif type(x) is bool:
            boolean = ET.Element("{%s}boolean" % _namespace)
            boolean.text = str(int(x))
            val.append(boolean)
        elif type(x) in (str, unicode):
            string = ET.Element("{%s}string" % _namespace)
            string.text = x
            val.append(string)
        elif type(x) is float:
            double = ET.Element("{%s}double" % _namespace)
            double.text = str(x)
            val.append(double)
        elif type(x) is rpcbase64:
            b64 = ET.Element("{%s}base64" % _namespace)
            b64.text = x.encoded()
            val.append(b64)
        elif type(x) is rpctime:
            iso = ET.Element("{%s}dateTime.iso8601" % _namespace)
            iso.text = str(x)
            val.append(iso)
        elif type(x) in (list, tuple):
            array = ET.Element("{%s}array" % _namespace)
            data = ET.Element("{%s}data" % _namespace)
            for y in x:
                data.append(_py2xml(y))
            array.append(data)
            val.append(array)
        elif type(x) is dict:
            struct = ET.Element("{%s}struct" % _namespace)
            for y in x.keys():
                member = ET.Element("{%s}member" % _namespace)
                name = ET.Element("{%s}name" % _namespace)
                name.text = y
                member.append(name)
                member.append(_py2xml(x[y]))
                struct.append(member)
            val.append(struct)
        return val

def xml2py(params):
    namespace = 'jabber:iq:rpc'
    vals = []
    for param in params.findall('{%s}param' % namespace):
        vals.append(_xml2py(param.find('{%s}value' % namespace)))
    return vals

def _xml2py(value):
    namespace = 'jabber:iq:rpc'
    if value.find('{%s}nil' % namespace) is not None:
        return None
    if value.find('{%s}i4' % namespace) is not None:
        return int(value.find('{%s}i4' % namespace).text)
    if value.find('{%s}int' % namespace) is not None:
        return int(value.find('{%s}int' % namespace).text)
    if value.find('{%s}boolean' % namespace) is not None:
        return bool(int(value.find('{%s}boolean' % namespace).text))
    if value.find('{%s}string' % namespace) is not None:
        return value.find('{%s}string' % namespace).text
    if value.find('{%s}double' % namespace) is not None:
        return float(value.find('{%s}double' % namespace).text)
    if value.find('{%s}base64' % namespace) is not None:
        return rpcbase64(value.find('{%s}base64' % namespace).text.encode())
    if value.find('{%s}Base64' % namespace) is not None:
        # Older versions of XEP-0009 used Base64
        return rpcbase64(value.find('{%s}Base64' % namespace).text.encode())
    if value.find('{%s}dateTime.iso8601' % namespace) is not None:
        return rpctime(value.find('{%s}dateTime.iso8601' % namespace).text)
    if value.find('{%s}struct' % namespace) is not None:
        struct = {}
        for member in value.find('{%s}struct' % namespace).findall('{%s}member' % namespace):
            struct[member.find('{%s}name' % namespace).text] = _xml2py(member.find('{%s}value' % namespace))
        return struct
    if value.find('{%s}array' % namespace) is not None:
        array = []
        for val in value.find('{%s}array' % namespace).find('{%s}data' % namespace).findall('{%s}value' % namespace):
            array.append(_xml2py(val))
        return array
    raise ValueError()



class rpcbase64(object):

    def __init__(self, data):
        #base 64 encoded string
        self.data = data

    def decode(self):
        return base64.b64decode(self.data)

    def __str__(self):
        return self.decode().decode()

    def encoded(self):
        return self.data.decode()



class rpctime(object):

    def __init__(self,data=None):
        #assume string data is in iso format YYYYMMDDTHH:MM:SS
        if type(data) in (str, unicode):
            self.timestamp = time.strptime(data,"%Y%m%dT%H:%M:%S")
        elif type(data) is time.struct_time:
            self.timestamp = data
        elif data is None:
            self.timestamp = time.gmtime()
        else:
            raise ValueError()

    def iso8601(self):
        #return a iso8601 string
        return time.strftime("%Y%m%dT%H:%M:%S",self.timestamp)

    def __str__(self):
        return self.iso8601()
