# Copyright (c) 2009, Rotem Yaari <vmalloc@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of organization nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Rotem Yaari ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Rotem Yaari BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
class CommandString(object):
    """
    >>> CommandString('a', 'b', 'c')
    a b c
    >>> CommandString('a', 'b', None, 'c')
    a b c
    """
    def __init__(self, *args):
        self.command = ""
        for arg in args:
            if not arg:
                continue
            if self.command:
                self.command += " "
            self.command += str(arg)
    def __repr__(self):
        return self.command

def quote_for_shell(s):
    """
    >>> print quote_for_shell('this is a " string')
    "this is a \\" string"
    >>> print quote_for_shell('this is a $shell variable')
    "this is a \\$shell variable"
    >>> print quote_for_shell(r'an escaped \\$')
    "an escaped \\\\\\$"
    """
    returned = s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    if " " in returned:
        returned = '"%s"' % returned
    return returned

if __name__ == '__main__':
    import doctest
    doctest.testmod()
