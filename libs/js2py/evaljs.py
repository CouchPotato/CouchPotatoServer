# coding=utf-8
""" This module is still experimental!
"""
from .translators import translate_js, DEFAULT_HEADER
import sys
import time
import json
import six
import os
import hashlib
import codecs



__all__  = ['EvalJs', 'translate_js', 'import_js', 'eval_js', 'translate_file', 'run_file']
DEBUG = False

def path_as_local(path):
    if os.path.isabs(path):
        return path
    # relative to cwd
    return os.path.join(os.getcwd(), path)

def import_js(path, lib_name, globals):
    """Imports from javascript source file.
      globals is your globals()"""
    with codecs.open(path_as_local(path), "r", "utf-8") as f:
        js = f.read()
    e = EvalJs()
    e.execute(js)
    var = e.context['var']
    globals[lib_name] = var.to_python()


def get_file_contents(path_or_file):
    if hasattr(path_or_file, 'read'):
        js = path_or_file.read()
    else:
        with codecs.open(path_as_local(path_or_file), "r", "utf-8") as f:
            js = f.read()
    return js


def write_file_contents(path_or_file, contents):
    if hasattr(path_or_file, 'write'):
        path_or_file.write(contents)
    else:
        with open(path_as_local(path_or_file), 'w') as f:
            f.write(contents)

def translate_file(input_path, output_path):
    '''
    Translates input JS file to python and saves the it to the output path.
    It appends some convenience code at the end so that it is easy to import JS objects.

    For example we have a file 'example.js' with:   var a = function(x) {return x}
    translate_file('example.js', 'example.py')

    Now example.py can be easily importend and used:
    >>> from example import example
    >>> example.a(30)
    30
    '''
    js = get_file_contents(input_path)

    py_code = translate_js(js)
    lib_name = os.path.basename(output_path).split('.')[0]
    head = '__all__ = [%s]\n\n# Don\'t look below, you will not understand this Python code :) I don\'t.\n\n' % repr(lib_name)
    tail = '\n\n# Add lib to the module scope\n%s = var.to_python()' % lib_name
    out = head + py_code + tail
    write_file_contents(output_path, out)






def run_file(path_or_file, context=None):
    ''' Context must be EvalJS object. Runs given path as a JS program. Returns (eval_value, context).
    '''
    if context is None:
        context = EvalJs()
    if not isinstance(context, EvalJs):
        raise TypeError('context must be the instance of EvalJs')
    eval_value = context.eval(get_file_contents(path_or_file))
    return eval_value, context



def eval_js(js):
    """Just like javascript eval. Translates javascript to python,
       executes and returns python object.
       js is javascript source code

       EXAMPLE:
        >>> import js2py
        >>> add = js2py.eval_js('function add(a, b) {return a + b}')
        >>> add(1, 2) + 3
        6
        >>> add('1', 2, 3)
        u'12'
        >>> add.constructor
        function Function() { [python code] }

       NOTE: For Js Number, String, Boolean and other base types returns appropriate python BUILTIN type.
       For Js functions and objects, returns Python wrapper - basically behaves like normal python object.
       If you really want to convert object to python dict you can use to_dict method.
       """
    e = EvalJs()
    return e.eval(js)



class EvalJs(object):
    """This class supports continuous execution of javascript under same context.

        >>> js = EvalJs()
        >>> js.execute('var a = 10;function f(x) {return x*x};')
        >>> js.f(9)
        81
        >>> js.a
        10

        context is a python dict or object that contains python variables that should be available to JavaScript
        For example:
        >>> js = EvalJs({'a': 30})
        >>> js.execute('var x = a')
        >>> js.x
        30

       You can run interactive javascript console with console method!"""
    def __init__(self, context={}):
        self.__dict__['_context'] = {}
        exec(DEFAULT_HEADER, self._context)
        self.__dict__['_var'] = self._context['var'].to_python()
        if not isinstance(context, dict):
            try:
                context = context.__dict__
            except:
                raise TypeError('context has to be either a dict or have __dict__ attr')
        for k, v in six.iteritems(context):
            setattr(self._var, k, v)

    def execute(self, js=None, use_compilation_plan=False):
        """executes javascript js in current context

        During initial execute() the converted js is cached for re-use. That means next time you
        run the same javascript snippet you save many instructions needed to parse and convert the
        js code to python code.

        This cache causes minor overhead (a cache dicts is updated) but the Js=>Py conversion process
        is typically expensive compared to actually running the generated python code.

        Note that the cache is just a dict, it has no expiration or cleanup so when running this
        in automated situations with vast amounts of snippets it might increase memory usage.
        """
        try:
            cache = self.__dict__['cache']
        except KeyError:
            cache = self.__dict__['cache'] = {}
        hashkey = hashlib.md5(js.encode('utf-8')).digest()
        try:
            compiled = cache[hashkey]
        except KeyError:
            code = translate_js(js, '', use_compilation_plan=use_compilation_plan)
            compiled = cache[hashkey] = compile(code, '<EvalJS snippet>', 'exec')
        exec(compiled, self._context)

    def eval(self, expression, use_compilation_plan=False):
        """evaluates expression in current context and returns its value"""
        code = 'PyJsEvalResult = eval(%s)'%json.dumps(expression)
        self.execute(code, use_compilation_plan=use_compilation_plan)
        return self['PyJsEvalResult']

    def execute_debug(self, js):
        """executes javascript js in current context
        as opposed to the (faster) self.execute method, you can use your regular debugger
        to set breakpoints and inspect the generated python code
        """
        code = translate_js(js, '')
        # make sure you have a temp folder:
        filename = 'temp' + os.sep + '_' + hashlib.md5(code).hexdigest() + '.py'
        try:
            with open(filename, mode='w') as f:
                f.write(code)
            execfile(filename, self._context)
        except Exception as err:
            raise err
        finally:
            os.remove(filename)
            try:
                os.remove(filename + 'c')
            except:
                pass

    def eval_debug(self, expression):
        """evaluates expression in current context and returns its value
        as opposed to the (faster) self.execute method, you can use your regular debugger
        to set breakpoints and inspect the generated python code
        """
        code = 'PyJsEvalResult = eval(%s)'%json.dumps(expression)
        self.execute_debug(code)
        return self['PyJsEvalResult']

    def __getattr__(self, var):
        return getattr(self._var, var)

    def __getitem__(self, var):
        return getattr(self._var, var)

    def __setattr__(self, var, val):
        return setattr(self._var, var, val)

    def __setitem__(self, var, val):
        return setattr(self._var, var, val)

    def console(self):
        """starts to interact (starts interactive console) Something like code.InteractiveConsole"""
        while True:
            if six.PY2:
                code = raw_input('>>> ')
            else:
                code = input('>>>')
            try:
                print(self.eval(code))
            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                if DEBUG:
                    sys.stderr.write(traceback.format_exc())
                else:
                    sys.stderr.write('EXCEPTION: '+str(e)+'\n')
                time.sleep(0.01)




#print x



if __name__=='__main__':
    #with open('C:\Users\Piotrek\Desktop\esprima.js', 'rb') as f:
    #    x = f.read()
    e = EvalJs()
    e.execute('square(x)')
    #e.execute(x)
    e.console()

