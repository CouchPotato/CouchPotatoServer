from js2py.base import *

@Js
def console():
    pass

@Js
def log():
    print(arguments[0])

console.put('log', log)