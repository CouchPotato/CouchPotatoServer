# Linktastic Module
# - A python2/3 compatible module that can create hardlinks/symlinks on windows-based systems
#
# Linktastic is distributed under the MIT License.  The follow are the terms and conditions of using Linktastic.
#
# The MIT License (MIT)
#  Copyright (c) 2012 Solipsis Development
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import subprocess
from subprocess import CalledProcessError
import os


# Prevent spaces from messing with us!
def _escape_param(param):
	return '"%s"' % param


# Private function to create link on nt-based systems
def _link_windows(src, dest):
	try:
		subprocess.check_output(
			'cmd /C mklink /H %s %s' % (_escape_param(dest), _escape_param(src)),
			stderr=subprocess.STDOUT)
	except CalledProcessError as err:

		raise IOError(err.output.decode('utf-8'))

	# TODO, find out what kind of messages Windows sends us from mklink
	# print(stdout)
	# assume if they ret-coded 0 we're good


def _symlink_windows(src, dest):
	try:
		subprocess.check_output(
			'cmd /C mklink %s %s' % (_escape_param(dest), _escape_param(src)),
			stderr=subprocess.STDOUT)
	except CalledProcessError as err:
		raise IOError(err.output.decode('utf-8'))

	# TODO, find out what kind of messages Windows sends us from mklink
	# print(stdout)
	# assume if they ret-coded 0 we're good


# Create a hard link to src named as dest
# This version of link, unlike os.link, supports nt systems as well
def link(src, dest):
	if os.name == 'nt':
		_link_windows(src, dest)
	else:
		os.link(src, dest)


# Create a symlink to src named as dest, but don't fail if you're on nt
def symlink(src, dest):
	if os.name == 'nt':
		_symlink_windows(src, dest)
	else:
		os.symlink(src, dest)
