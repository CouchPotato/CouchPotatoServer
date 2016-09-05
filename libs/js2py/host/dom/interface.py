from StringIO import StringIO
from constants import *
from bs4 import BeautifulSoup
from js2py.base import *
try:
    import lxml
    def parse(source):
        return BeautifulSoup(source, 'lxml')
except:
    def parse(source):
        return BeautifulSoup(source)







x = '''<table>
  <tbody>
    <tr>
      <td>Shady Grove</td>
      <td>Aeolian</td>
    </tr>
    <tr>
      <td>Over the River, Charlie</td>
      <td>Dorian</td>
    </tr>
  </tbody>
</table>'''



class DOM(PyJs):
    prototype = ObjectPrototype
    def __init__(self):
        self.own = {}

    def readonly(self, name, val):
        self.define_own_property(name, {'writable':False, 'enumerable':False, 'configurable':False, 'value': Js(val)})



# DOMStringList

class DOMStringListPrototype(DOM):
    Class = 'DOMStringListPrototype'

    def contains(element):
        return element.to_string().value in this._string_list

    def item(index):
        return this._string_list[index.to_int()] if 0<=index.to_int()<len(this._string_list) else index.null


class DOMStringList(DOM):
    Class = 'DOMStringList'
    prototype = compose_prototype(DOMStringListPrototype)
    def __init__(self, _string_list):
        self.own = {}

        self._string_list = _string_list


# NameList

class NameListPrototype(DOM):






