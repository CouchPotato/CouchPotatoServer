# Copyright (c) 2003-2005 Jimmy Retzlaff, 2008 Konstantin Yegupov
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Unix version uses unrar command line executable

import subprocess
import gc

import os, os.path
import time, re

from rar_exceptions import *

class UnpackerNotInstalled(Exception): pass

rar_executable_cached = None
rar_executable_version = None

def call_unrar(params):
    "Calls rar/unrar command line executable, returns stdout pipe"
    global rar_executable_cached
    if rar_executable_cached is None:
        for command in ('unrar', 'rar'):
            try:
                subprocess.Popen([command], stdout=subprocess.PIPE)
                rar_executable_cached = command
                break
            except OSError:
                pass
        if rar_executable_cached is None:
            raise UnpackerNotInstalled("No suitable RAR unpacker installed")
            
    assert type(params) == list, "params must be list"
    args = [rar_executable_cached] + params
    try:
        gc.disable() # See http://bugs.python.org/issue1336
        return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        gc.enable()

class RarFileImplementation(object):

    def init(self, password=None):
        global rar_executable_version
        self.password = password
        
        
        stdoutdata, stderrdata = self.call('v', []).communicate()
        
        for line in stderrdata.splitlines():
            if line.strip().startswith("Cannot open"):
                raise FileOpenError
            if line.find("CRC failed")>=0:
                raise IncorrectRARPassword   
        accum = []
        source = iter(stdoutdata.splitlines())
        line = ''
        while not (line.startswith('UNRAR')):
            line = source.next()
        signature = line
        # The code below is mighty flaky
        # and will probably crash on localized versions of RAR
        # but I see no safe way to rewrite it using a CLI tool
        if signature.startswith("UNRAR 4"):
            rar_executable_version = 4
            while not (line.startswith('Comment:') or line.startswith('Pathname/Comment')):
                if line.strip().endswith('is not RAR archive'):
                    raise InvalidRARArchive
                line = source.next()
            while not line.startswith('Pathname/Comment'):
                accum.append(line.rstrip('\n'))
                line = source.next()
            if len(accum):
                accum[0] = accum[0][9:] # strip out "Comment:" part
                self.comment = '\n'.join(accum[:-1])
            else:
                self.comment = None
        elif signature.startswith("UNRAR 5"):
            rar_executable_version = 5
            line = source.next()
            while not line.startswith('Archive:'):
                if line.strip().endswith('is not RAR archive'):
                    raise InvalidRARArchive
                accum.append(line.rstrip('\n'))
                line = source.next()
            if len(accum):
                self.comment = '\n'.join(accum[:-1]).strip()
            else:
                self.comment = None
        else:
            raise UnpackerNotInstalled("Unsupported RAR version, expected 4.x or 5.x, found: " 
                    + signature.split(" ")[1])
                
                
    def escaped_password(self):
        return '-' if self.password == None else self.password
        
        
    def call(self, cmd, options=[], files=[]):
        options2 = options + ['p'+self.escaped_password()]
        soptions = ['-'+x for x in options2]
        return call_unrar([cmd]+soptions+['--',self.archiveName]+files)

    def infoiter(self):
        
        command = "v" if rar_executable_version == 4 else "l"
        stdoutdata, stderrdata = self.call(command, ['c-']).communicate()
        
        for line in stderrdata.splitlines():
            if line.strip().startswith("Cannot open"):
                raise FileOpenError
            
        accum = []
        source = iter(stdoutdata.splitlines())
        line = ''
        while not line.startswith('-----------'):
            if line.strip().endswith('is not RAR archive'):
                raise InvalidRARArchive
            if line.startswith("CRC failed") or line.startswith("Checksum error"):
                raise IncorrectRARPassword  
            line = source.next()
        line = source.next()
        i = 0
        re_spaces = re.compile(r"\s+")
        if rar_executable_version == 4:
            while not line.startswith('-----------'):
                accum.append(line)
                if len(accum)==2:
                    data = {}
                    data['index'] = i
                    # asterisks mark password-encrypted files
                    data['filename'] = accum[0].strip().lstrip("*") # asterisks marks password-encrypted files
                    fields = re_spaces.split(accum[1].strip())
                    data['size'] = int(fields[0])
                    attr = fields[5]
                    data['isdir'] = 'd' in attr.lower()
                    data['datetime'] = time.strptime(fields[3]+" "+fields[4], '%d-%m-%y %H:%M')
                    data['comment'] = None
                    yield data
                    accum = []
                    i += 1
                line = source.next()
        elif rar_executable_version == 5:
            while not line.startswith('-----------'):
                fields = line.strip().lstrip("*").split()
                data = {}
                data['index'] = i
                data['filename'] = " ".join(fields[4:])
                data['size'] = int(fields[1])
                attr = fields[0]
                data['isdir'] = 'd' in attr.lower()
                data['datetime'] = time.strptime(fields[2]+" "+fields[3], '%d-%m-%y %H:%M')
                data['comment'] = None
                yield data
                i += 1
                line = source.next()
            

    def read_files(self, checker):
        res = []
        for info in self.infoiter():
            checkres = checker(info)
            if checkres==True and not info.isdir:
                pipe = self.call('p', ['inul'], [info.filename]).stdout
                res.append((info, pipe.read()))
        return res            

          
    def extract(self, checker, path, withSubpath, overwrite):
        res = []
        command = 'x'
        if not withSubpath:
            command = 'e'
        options = []
        if overwrite:
            options.append('o+')
        else:
            options.append('o-')
        if not path.endswith(os.sep):
            path += os.sep
        names = []
        for info in self.infoiter():
            checkres = checker(info)
            if type(checkres) in [str, unicode]:
                raise NotImplementedError("Condition callbacks returning strings are deprecated and only supported in Windows")
            if checkres==True and not info.isdir:
                names.append(info.filename)
                res.append(info)
        names.append(path)
        proc = self.call(command, options, names)
        stdoutdata, stderrdata = proc.communicate()
        if stderrdata.find("CRC failed")>=0 or stderrdata.find("Checksum error")>=0:
            raise IncorrectRARPassword  
        return res            
            
    def destruct(self):
        pass

    
