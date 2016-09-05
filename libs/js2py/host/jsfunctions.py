from js2py.base import *

RADIX_CHARS = {'1': 1, '0': 0, '3': 3, '2': 2, '5': 5, '4': 4, '7': 7, '6': 6, '9': 9, '8': 8, 'a': 10, 'c': 12,
               'b': 11, 'e': 14, 'd': 13, 'g': 16, 'f': 15, 'i': 18, 'h': 17, 'k': 20, 'j': 19, 'm': 22, 'l': 21,
               'o': 24, 'n': 23, 'q': 26, 'p': 25, 's': 28, 'r': 27, 'u': 30, 't': 29, 'w': 32, 'v': 31, 'y': 34,
               'x': 33, 'z': 35, 'A': 10, 'C': 12, 'B': 11, 'E': 14, 'D': 13, 'G': 16, 'F': 15, 'I': 18, 'H': 17,
               'K': 20, 'J': 19, 'M': 22, 'L': 21, 'O': 24, 'N': 23, 'Q': 26, 'P': 25, 'S': 28, 'R': 27, 'U': 30,
               'T': 29, 'W': 32, 'V': 31, 'Y': 34, 'X': 33, 'Z': 35}
@Js
def parseInt (string , radix):
    string = string.to_string().value.lstrip()
    sign = 1
    if string and string[0] in {'+', '-'}:
        if string[0]=='-':
            sign = -1
        string = string[1:]
    r = radix.to_int32()
    strip_prefix = True
    if r:
        if r<2 or r>36:
            return NaN
        if r!=16:
            strip_prefix = False
    else:
        r = 10
    if strip_prefix:
        if len(string)>=2 and string[:2] in {'0x', '0X'}:
            string = string[2:]
            r = 16
    n = 0
    num  = 0
    while n<len(string):
        cand = RADIX_CHARS.get(string[n])
        if cand is None or not cand < r:
            break
        num = cand + num*r
        n += 1
    if not n:
        return NaN
    return sign*num

@Js
def parseFloat(string):
    string = string.to_string().value.strip()
    sign = 1
    if string and string[0] in {'+', '-'}:
        if string[0]=='-':
            sign = -1
        string = string[1:]
    num = None
    length = 1
    max_len = None
    failed = 0
    while length<=len(string):
        try:
            num = float(string[:length])
            max_len = length
            failed = 0
        except:
            failed += 1
            if failed>4: # cant be a number anymore
                break
        length += 1
    if num is None:
        return NaN
    return sign*float(string[:max_len])

@Js
def isNaN(number):
    if number.to_number().is_nan():
        return true
    return false

@Js
def isFinite(number):
    num = number.to_number()
    if num.is_nan() or num.is_infinity():
        return false
    return true


#todo URI handling!



