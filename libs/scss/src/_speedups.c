/*
* pyScss, a Scss compiler for Python
* SCSS blocks scanner.
*
* German M. Bravo (Kronuz) <german.mb@gmail.com>
* https://github.com/Kronuz/pyScss
*
* MIT license (http://www.opensource.org/licenses/mit-license.php)
* Copyright (c) 2011 German M. Bravo (Kronuz), All rights reserved.
*/
#include <Python.h>
#include "block_locator.h"
#include "scanner.h"

/* BlockLocator */
staticforward PyTypeObject scss_BlockLocatorType;

typedef struct {
	PyObject_HEAD
	BlockLocator *locator;
} scss_BlockLocator;

static int
scss_BlockLocator_init(scss_BlockLocator *self, PyObject *args, PyObject *kwds)
{
	char *codestr;
	int codestr_sz;

	self->locator = NULL;

	if (!PyArg_ParseTuple(args, "s#", &codestr, &codestr_sz)) {
		return -1;
	}

	self->locator = BlockLocator_new(codestr, codestr_sz);

	#ifdef DEBUG
		PySys_WriteStderr("Scss BlockLocator object initialized! (%lu bytes)\n", sizeof(scss_BlockLocator));
	#endif

	return 0;
}

static void
scss_BlockLocator_dealloc(scss_BlockLocator *self)
{
	if (self->locator != NULL) BlockLocator_del(self->locator);

	self->ob_type->tp_free((PyObject*)self);

	#ifdef DEBUG
		PySys_WriteStderr("Scss BlockLocator object destroyed!\n");
	#endif
}

scss_BlockLocator*
scss_BlockLocator_iter(scss_BlockLocator *self)
{
	Py_INCREF(self);
	return self;
}

PyObject*
scss_BlockLocator_iternext(scss_BlockLocator *self)
{
	Block *block;

	if (self->locator != NULL) {
		block = BlockLocator_iternext(self->locator);

		if (block->error > 0) {
			return Py_BuildValue(
				"is#s#",
				block->lineno,
				block->selprop,
				block->selprop_sz,
				block->codestr,
				block->codestr_sz
			);
		}

		if (block->error > 0) {
			PyErr_SetString(PyExc_Exception, self->locator->exc);
			return NULL;
		}
	}

	/* Raising of standard StopIteration exception with empty value. */
	PyErr_SetNone(PyExc_StopIteration);
	return NULL;
}

/* Type definition */

static PyTypeObject scss_BlockLocatorType = {
	PyObject_HEAD_INIT(NULL)
	0,                                         /* ob_size */
	"scss._BlockLocator",                      /* tp_name */
	sizeof(scss_BlockLocator),                 /* tp_basicsize */
	0,                                         /* tp_itemsize */
	(destructor)scss_BlockLocator_dealloc,     /* tp_dealloc */
	0,                                         /* tp_print */
	0,                                         /* tp_getattr */
	0,                                         /* tp_setattr */
	0,                                         /* tp_compare */
	0,                                         /* tp_repr */
	0,                                         /* tp_as_number */
	0,                                         /* tp_as_sequence */
	0,                                         /* tp_as_mapping */
	0,                                         /* tp_hash  */
	0,                                         /* tp_call */
	0,                                         /* tp_str */
	0,                                         /* tp_getattro */
	0,                                         /* tp_setattro */
	0,                                         /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_ITER, /* tp_flags */
	"Internal BlockLocator iterator object.",  /* tp_doc */
	0,                                         /* tp_traverse */
	0,                                         /* tp_clear */
	0,                                         /* tp_richcompare */
	0,                                         /* tp_weaklistoffset */
	(getiterfunc)scss_BlockLocator_iter,       /* tp_iter: __iter__() method */
	(iternextfunc)scss_BlockLocator_iternext,  /* tp_iternext: next() method */
	0,                                         /* tp_methods */
	0,                                         /* tp_members */
	0,                                         /* tp_getset */
	0,                                         /* tp_base */
	0,                                         /* tp_dict */
	0,                                         /* tp_descr_get */
	0,                                         /* tp_descr_set */
	0,                                         /* tp_dictoffset */
	(initproc)scss_BlockLocator_init,          /* tp_init */
};


/* Scanner */
static PyObject *PyExc_scss_NoMoreTokens;

staticforward PyTypeObject scss_ScannerType;

typedef struct {
	PyObject_HEAD
	Scanner *scanner;
} scss_Scanner;


static PyObject *
scss_Scanner_rewind(scss_Scanner *self, PyObject *args)
{
	int token_num;
	if (self->scanner != NULL) {
		if (PyArg_ParseTuple(args, "i", &token_num)) {
			Scanner_rewind(self->scanner, token_num);
		}
	}
	Py_INCREF(Py_None);
	return (PyObject *)Py_None;
}


static PyObject *
scss_Scanner_token(scss_Scanner *self, PyObject *args)
{
	PyObject *iter;
	PyObject *item;
	long size;

	Token *p_token;

	int token_num;
	PyObject *restrictions = NULL;
	Pattern *_restrictions = NULL;
	int restrictions_sz = 0;
	if (self->scanner != NULL) {
		if (PyArg_ParseTuple(args, "i|O", &token_num, &restrictions)) {
			if (restrictions != NULL) {
				size = PySequence_Size(restrictions);
				if (size != -1) {
					_restrictions = PyMem_New(Pattern, size);
					iter = PyObject_GetIter(restrictions);
					while ((item = PyIter_Next(iter))) {
						if (PyString_Check(item)) {
							_restrictions[restrictions_sz].tok = PyString_AsString(item);
							_restrictions[restrictions_sz].expr = NULL;
							restrictions_sz++;
						}
						Py_DECREF(item);
					}
					Py_DECREF(iter);
				}
			}
			p_token = Scanner_token(self->scanner, token_num, _restrictions, restrictions_sz);

			if (_restrictions != NULL) PyMem_Del(_restrictions);

			if (p_token == (Token *)SCANNER_EXC_BAD_TOKEN) {
				PyErr_SetString(PyExc_SyntaxError, self->scanner->exc);
				return NULL;
			}
			if (p_token == (Token *)SCANNER_EXC_RESTRICTED) {
				PyErr_SetString(PyExc_SyntaxError, self->scanner->exc);
				return NULL;
			}
			if (p_token == (Token *)SCANNER_EXC_UNIMPLEMENTED) {
				PyErr_SetString(PyExc_NotImplementedError, self->scanner->exc);
				return NULL;
			}
			if (p_token == (Token *)SCANNER_EXC_NO_MORE_TOKENS) {
				PyErr_SetNone(PyExc_scss_NoMoreTokens);
				return NULL;
			}
			if (p_token < 0) {
				PyErr_SetNone(PyExc_Exception);
				return NULL;
			}
			return Py_BuildValue(
				"iiss#",
				p_token->string - self->scanner->input,
				p_token->string - self->scanner->input + p_token->string_sz,
				p_token->regex->tok,
				p_token->string,
				p_token->string_sz
			);
		}
	}
	Py_INCREF(Py_None);
	return (PyObject *)Py_None;
}

static PyObject *
scss_Scanner_reset(scss_Scanner *self, PyObject *args, PyObject *kwds)
{
	char *input = NULL;
	int input_sz = 0;

	if (self->scanner != NULL) {
		if (PyArg_ParseTuple(args, "|z#", &input, &input_sz)) {
			Scanner_reset(self->scanner, input, input_sz);
		}
	}

	Py_INCREF(Py_None);
	return (PyObject *)Py_None;
}

static PyObject *
scss_Scanner_setup_patterns(PyObject *self, PyObject *patterns)
{
	PyObject *item, *item0, *item1;
	int i, is_tuple, _is_tuple;
	long size;

	Pattern *_patterns = NULL;
	int patterns_sz = 0;
	if (!Scanner_initialized()) {
		is_tuple = PyTuple_Check(patterns);
		if (is_tuple || PyList_Check(patterns)) {
			size = is_tuple ? PyTuple_Size(patterns) : PyList_Size(patterns);
			_patterns = PyMem_New(Pattern, size);
			for (i = 0; i < size; ++i) {
				item = is_tuple ? PyTuple_GetItem(patterns, i) : PyList_GetItem(patterns, i);
				_is_tuple = PyTuple_Check(item);
				if (_is_tuple || PyList_Check(item)) {
					item0 = _is_tuple ? PyTuple_GetItem(item, 0) : PyList_GetItem(item, 0);
					item1 = _is_tuple ? PyTuple_GetItem(item, 1) : PyList_GetItem(item, 1);
					if (PyString_Check(item0) && PyString_Check(item1)) {
						_patterns[patterns_sz].tok = PyString_AsString(item0);
						_patterns[patterns_sz].expr = PyString_AsString(item1);
						patterns_sz++;
					}
				}
			}
		}
		Scanner_initialize(_patterns, patterns_sz);
		if (_patterns != NULL) PyMem_Del(_patterns);
	}
	Py_INCREF(Py_None);
	return (PyObject *)Py_None;
}

static int
scss_Scanner_init(scss_Scanner *self, PyObject *args, PyObject *kwds)
{
	PyObject *item, *item0, *item1;
	int i, is_tuple, _is_tuple;
	long size;

	PyObject *patterns, *ignore;
	Pattern *_patterns = NULL;
	int patterns_sz = 0;
	Pattern *_ignore = NULL;
	int ignore_sz = 0;
	char *input = NULL;
	int input_sz = 0;

	self->scanner = NULL;

	if (!PyArg_ParseTuple(args, "OO|z#", &patterns, &ignore, &input, &input_sz)) {
		return -1;
	}

	if (!Scanner_initialized()) {
		is_tuple = PyTuple_Check(patterns);
		if (is_tuple || PyList_Check(patterns)) {
			size = is_tuple ? PyTuple_Size(patterns) : PyList_Size(patterns);
			_patterns = PyMem_New(Pattern, size);
			for (i = 0; i < size; ++i) {
				item = is_tuple ? PyTuple_GetItem(patterns, i) : PyList_GetItem(patterns, i);
				_is_tuple = PyTuple_Check(item);
				if (_is_tuple || PyList_Check(item)) {
					item0 = _is_tuple ? PyTuple_GetItem(item, 0) : PyList_GetItem(item, 0);
					item1 = _is_tuple ? PyTuple_GetItem(item, 1) : PyList_GetItem(item, 1);
					if (PyString_Check(item0) && PyString_Check(item1)) {
						_patterns[patterns_sz].tok = PyString_AsString(item0);
						_patterns[patterns_sz].expr = PyString_AsString(item1);
						patterns_sz++;
					}
				}
			}
		}
		Scanner_initialize(_patterns, patterns_sz);
	}

	is_tuple = PyTuple_Check(ignore);
	if (is_tuple || PyList_Check(ignore)) {
		size = is_tuple ? PyTuple_Size(ignore) : PyList_Size(ignore);
		_ignore = PyMem_New(Pattern, size);
		for (i = 0; i < size; ++i) {
			item = is_tuple ? PyTuple_GetItem(ignore, i) : PyList_GetItem(ignore, i);
			if (PyString_Check(item)) {
				_ignore[ignore_sz].tok = PyString_AsString(item);
				_ignore[ignore_sz].expr = NULL;
				ignore_sz++;
			}
		}
	}

	self->scanner = Scanner_new(_patterns, patterns_sz, _ignore, ignore_sz, input, input_sz);

	if (_patterns != NULL) PyMem_Del(_patterns);
	if (_ignore != NULL) PyMem_Del(_ignore);

	#ifdef DEBUG
		PySys_WriteStderr("Scss Scanner object initialized! (%lu bytes)\n", sizeof(scss_Scanner));
	#endif

	return 0;
}

static PyObject *
scss_Scanner_repr(scss_Scanner *self)
{
	/* Print the last 10 tokens that have been scanned in */
	PyObject *repr, *tmp;
	Token *p_token;
	int i, start, pos;

	if (self->scanner != NULL && self->scanner->tokens_sz) {
		start = self->scanner->tokens_sz - 10;
		repr = PyString_FromString("");
		for (i = (start < 0) ? 0 : start; i < self->scanner->tokens_sz; i++) {
			p_token = &self->scanner->tokens[i];
			PyString_ConcatAndDel(&repr, PyString_FromString("\n"));
			pos = (int)(p_token->string - self->scanner->input);
			PyString_ConcatAndDel(&repr, PyString_FromFormat("  (@%d)  %s  =  ",
				pos, p_token->regex->tok));
			tmp = PyString_FromStringAndSize(p_token->string, p_token->string_sz);
			PyString_ConcatAndDel(&repr, PyObject_Repr(tmp));
			Py_XDECREF(tmp);
		}
	} else {
		repr = PyString_FromString("None");
	}

	return (PyObject *)repr;

/*
	PyObject *repr, *tmp, *tmp2;
	Token *p_token;
	char *tok;
	int i, start, first = 1, cur, max=0, pos;

	if (self->scanner != NULL && self->scanner->tokens_sz) {
		start = self->scanner->tokens_sz - 10;
		repr = PyString_FromString("");
		for (i = (start < 0) ? 0 : start; i < self->scanner->tokens_sz; i++) {
			p_token = self->scanner->tokens[i];
			PyString_ConcatAndDel(&repr, PyString_FromString("\n"));
			pos = (int)(p_token->string - self->scanner->input);
			PyString_ConcatAndDel(&repr, PyString_FromFormat("  (@%d)  %s  =  ",
				pos, p_token->regex->tok));
			tmp = PyString_FromString(p_token->string);
			PyString_ConcatAndDel(&repr, PyObject_Repr(tmp));
			Py_XDECREF(tmp);
		}

		start = self->scanner->tokens_sz - 10;
		for (i = (start < 0) ? 0 : start; i < self->scanner->tokens_sz; i++) {
			p_token = self->scanner->tokens[i];
			cur = strlen(p_token->regex->tok) * 2;
			if (cur > max) max = cur;
		}
		tok = PyMem_New(char, max + 4);
		repr = PyString_FromString("");
		for (i = (start < 0) ? 0 : start; i < self->scanner->tokens_sz; i++) {
			p_token = self->scanner->tokens[i];
			if (!first) PyString_ConcatAndDel(&repr, PyString_FromString("\n"));

			pos = (int)(p_token->string - self->scanner->input);
			if (pos < 10) PyString_ConcatAndDel(&repr, PyString_FromString(" "));
			if (pos < 100) PyString_ConcatAndDel(&repr, PyString_FromString(" "));
			if (pos < 1000) PyString_ConcatAndDel(&repr, PyString_FromString(" "));
			PyString_ConcatAndDel(&repr, PyString_FromFormat("(@%d)  ",
				pos));

			tmp = PyString_FromString(p_token->regex->tok);
			tmp2 = PyObject_Repr(tmp);
			memset(tok, ' ', max + 4);
			tok[max + 3 - PyString_Size(tmp2)] = '\0';
			PyString_ConcatAndDel(&repr, PyString_FromString(tok));
			PyString_ConcatAndDel(&repr, tmp2);
			Py_XDECREF(tmp);

			PyString_ConcatAndDel(&repr, PyString_FromString("  =  "));
			tmp = PyString_FromString(p_token->string);
			PyString_ConcatAndDel(&repr, PyObject_Repr(tmp));
			Py_XDECREF(tmp);

			first = 0;
		}
		PyMem_Del(tok);
	} else {
		repr = PyString_FromString("None");
	}

	return (PyObject *)repr;
*/
}

static void
scss_Scanner_dealloc(scss_Scanner *self)
{
	if (self->scanner != NULL) Scanner_del(self->scanner);

	self->ob_type->tp_free((PyObject*)self);

	#ifdef DEBUG
		PySys_WriteStderr("Scss Scanner object destroyed!\n");
	#endif
}

static PyMethodDef scss_Scanner_methods[] = {
	{"reset", (PyCFunction)scss_Scanner_reset, METH_VARARGS, "Scan the next token"},
	{"token", (PyCFunction)scss_Scanner_token, METH_VARARGS, "Get the nth token"},
	{"rewind", (PyCFunction)scss_Scanner_rewind, METH_VARARGS, "Rewind scanner"},
	{"setup_patterns", (PyCFunction)scss_Scanner_setup_patterns, METH_O | METH_STATIC, "Initialize patterns."},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

static PyTypeObject scss_ScannerType = {
	PyObject_HEAD_INIT(NULL)
	0,                                         /* ob_size */
	"scss.Scanner",                            /* tp_name */
	sizeof(scss_Scanner),                      /* tp_basicsize */
	0,                                         /* tp_itemsize */
	(destructor)scss_Scanner_dealloc,          /* tp_dealloc */
	0,                                         /* tp_print */
	0,                                         /* tp_getattr */
	0,                                         /* tp_setattr */
	0,                                         /* tp_compare */
	(reprfunc)scss_Scanner_repr,               /* tp_repr */
	0,                                         /* tp_as_number */
	0,                                         /* tp_as_sequence */
	0,                                         /* tp_as_mapping */
	0,                                         /* tp_hash  */
	0,                                         /* tp_call */
	0,                                         /* tp_str */
	0,                                         /* tp_getattro */
	0,                                         /* tp_setattro */
	0,                                         /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /* tp_flags */
	"Scanner object.",                         /* tp_doc */
	0,                                         /* tp_traverse */
	0,                                         /* tp_clear */
	0,                                         /* tp_richcompare */
	0,                                         /* tp_weaklistoffset */
	0,                                         /* tp_iter: __iter__() method */
	0,                                         /* tp_iternext: next() method */
	scss_Scanner_methods,                      /* tp_methods */
	0,                                         /* tp_members */
	0,                                         /* tp_getset */
	0,                                         /* tp_base */
	0,                                         /* tp_dict */
	0,                                         /* tp_descr_get */
	0,                                         /* tp_descr_set */
	0,                                         /* tp_dictoffset */
	(initproc)scss_Scanner_init,               /* tp_init */
};


/* Python constructor */

static PyObject *
scss_locate_blocks(PyObject *self, PyObject *args)
{
	scss_BlockLocator *result = NULL;

	result = PyObject_New(scss_BlockLocator, &scss_BlockLocatorType);
	if (result) {
		scss_BlockLocator_init(result, args, NULL);
	}

	return (PyObject *)result;
}


/* Module functions */

static PyMethodDef scss_methods[] = {
	{"locate_blocks", (PyCFunction)scss_locate_blocks, METH_VARARGS, "Locate Scss blocks."},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};


/* Module init function */

PyMODINIT_FUNC
init_speedups(void)
{
	PyObject* m;

	scss_BlockLocatorType.tp_new = PyType_GenericNew;
	if (PyType_Ready(&scss_BlockLocatorType) < 0)
		return;

	scss_ScannerType.tp_new = PyType_GenericNew;
	if (PyType_Ready(&scss_ScannerType) < 0)
		return;

	BlockLocator_initialize();
	Scanner_initialize(NULL, 0);

	m = Py_InitModule("_speedups", scss_methods);

	Py_INCREF(&scss_BlockLocatorType);
	PyModule_AddObject(m, "_BlockLocator", (PyObject *)&scss_BlockLocatorType);

	Py_INCREF(&scss_ScannerType);
	PyModule_AddObject(m, "Scanner", (PyObject *)&scss_ScannerType);

	PyExc_scss_NoMoreTokens = PyErr_NewException("_speedups.NoMoreTokens", NULL, NULL);
	Py_INCREF(PyExc_scss_NoMoreTokens);
	PyModule_AddObject(m, "NoMoreTokens", (PyObject *)PyExc_scss_NoMoreTokens);
}
