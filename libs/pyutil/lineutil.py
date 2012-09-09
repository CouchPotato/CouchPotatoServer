#!/usr/bin/env python

import os, re

def lineify_fileobjs(ifo, ofo, strip=False):
	from pyutil.strutil import pop_trailing_newlines, split_on_newlines
	for l in ifo:
		for sl in split_on_newlines(pop_trailing_newlines(l)):
			if strip:
				sl = sl.strip()
			ofo.write(pop_trailing_newlines(sl) + '\n')

def lineify_file(fname, strip=False, nobak=True):
	f = open(fname, "rU")
	from pyutil.fileutil import ReopenableNamedTemporaryFile
	rntf = ReopenableNamedTemporaryFile()
	fo = open(rntf.name, "wb")
	for l in f:
		if strip:
			l = l.strip() + '\n'
		fo.write(l)
	fo.close()
	import shutil
	if not nobak:
		shutil.copyfile(fname, fname + ".lines.py-bak")
	import shutil
	try:
		shutil.move(rntf.name, fname)
	except EnvironmentError:
		# Couldn't atomically overwrite, so just hope that this process doesn't die
		# and the target file doesn't get recreated in between the following two
		# operations:
		if nobak:
			os.remove(fname)
		else:
			shutil.move(fname, fname + ".lines.py-bak-2")
		shutil.move(rntf.name, fname)

def darcs_metadir_dirpruner(dirs):
	if "_darcs" in dirs:
		dirs.remove("_darcs")

SCRE=re.compile("\\.(py|php|c|h|cpp|hpp|txt|sh|pyx|pxi|html|htm)$|makefile$", re.IGNORECASE)
def source_code_filepruner(fname):
	return SCRE.search(fname)

def all_filepruner(fname):
	return True

def all_dirpruner(dirs):
	return

def lineify_all_files(dirname, strip=False, nobak=True, dirpruner=all_dirpruner, filepruner=all_filepruner):
	for (root, dirs, files,) in os.walk(dirname):
		dirpruner(dirs)
		for fname in files:
			fullfname = os.path.join(root, fname)
			if filepruner(fullfname):
				lineify_file(fullfname, strip=strip, nobak=nobak)
