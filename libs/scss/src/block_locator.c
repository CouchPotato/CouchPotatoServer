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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "block_locator.h"

int _strip(char *begin, char *end, int *lineno) {
	// "    1\0     some,    \n  2\0 aca  "
	int _cnt,
		cnt = 0,
		pass = 1,
		addnl = 0;
	char c,
		*line = NULL,
		*first = begin,
		*last = begin,
		*write = lineno ? begin : NULL;
	while (begin < end) {
		c = *begin;
		if (c == '\0') {
			if (lineno && line == NULL) {
				line = first - 1;
				do {
					c = *++line;
				} while (c == ' ' || c == '\t' || c == '\n' || c == ';');
				if (c != '\0') {
					sscanf(line, "%d", lineno);
				}
			}
			first = last = begin + 1;
			pass = 1;
		} else if (c == '\n') {
			_cnt = (int)(last - first);
			if (_cnt > 0) {
				cnt += _cnt + addnl;
				if (write != NULL) {
					if (addnl) {
						*write++ = '\n';
					}
					while (first < last) {
						*write++ = *first++;
					}
					addnl = 1;
				}
			}
			first = last = begin + 1;
			pass = 1;
		} else if (c == ' ' || c == '\t') {
			if (pass) {
				first = last = begin + 1;
			}
		} else {
			last = begin + 1;
			pass = 0;
		}
		begin++;
	}
	_cnt = (int)(last - first);
	if (_cnt > 0) {
		cnt += _cnt + addnl;
		if (write != NULL) {
			if (addnl) {
				*write++ = '\n';
			}
			while (first < last) {
				*write++ = *first++;
			}
		}
	}
	return cnt;
}


/* BlockLocator */

typedef void _BlockLocator_Callback(BlockLocator*);

static void
_BlockLocator_start_string(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// A string starts
	self->instr = *(self->codestr_ptr);
}

static void
_BlockLocator_end_string(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// A string ends (FIXME: needs to accept escaped characters)
	self->instr = 0;
}

static void
_BlockLocator_start_parenthesis(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// parenthesis begins:
	self->par++;
	self->thin = NULL;
	self->safe = self->codestr_ptr + 1;
}

static void
_BlockLocator_end_parenthesis(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	self->par--;
}

static void
_BlockLocator_flush_properties(BlockLocator *self) {
	int len, lineno = -1;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// Flush properties
	if (self->lose <= self->init) {
		len = _strip(self->lose, self->init, &lineno);
		if (len) {
			if (lineno != -1) {
				self->lineno = lineno;
			}

			self->block.selprop = self->lose;
			self->block.selprop_sz = len;
			self->block.codestr = NULL;
			self->block.codestr_sz = 0;
			self->block.lineno = self->lineno;
			self->block.error = 1;
		}
		self->lose = self->init;
	}
}

static void
_BlockLocator_start_block1(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// Start block:
	if (self->codestr_ptr > self->codestr && *(self->codestr_ptr - 1) == '#') {
		self->skip = 1;
	} else {
		self->start = self->codestr_ptr;
		if (self->thin != NULL && _strip(self->thin, self->codestr_ptr, NULL)) {
			self->init = self->thin;
		}
		_BlockLocator_flush_properties(self);
		self->thin = NULL;
	}
	self->depth++;
}

static void
_BlockLocator_start_block(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// Start block:
	self->depth++;
}

static void
_BlockLocator_end_block1(BlockLocator *self) {
	int len, lineno = -1;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// Block ends:
	self->depth--;
	if (!self->skip) {
		self->end = self->codestr_ptr;
		len = _strip(self->init, self->start, &lineno);
		if (lineno != -1) {
			self->lineno = lineno;
		}

		self->block.selprop = self->init;
		self->block.selprop_sz = len;
		self->block.codestr = (self->start + 1);
		self->block.codestr_sz = (int)(self->end - (self->start + 1));
		self->block.lineno = self->lineno;
		self->block.error = 1;

		self->init = self->safe = self->lose = self->end + 1;
		self->thin = NULL;
	}
	self->skip = 0;
}

static void
_BlockLocator_end_block(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// Block ends:
	self->depth--;
}

static void
_BlockLocator_end_property(BlockLocator *self) {
	int len, lineno = -1;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// End of property (or block):
	self->init = self->codestr_ptr;
	if (self->lose <= self->init) {
		len = _strip(self->lose, self->init, &lineno);
		if (len) {
			if (lineno != -1) {
				self->lineno = lineno;
			}

			self->block.selprop = self->lose;
			self->block.selprop_sz = len;
			self->block.codestr = NULL;
			self->block.codestr_sz = 0;
			self->block.lineno = self->lineno;
			self->block.error = 1;
		}
		self->init = self->safe = self->lose = self->codestr_ptr + 1;
	}
	self->thin = NULL;
}

static void
_BlockLocator_mark_safe(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// We are on a safe zone
	if (self->thin != NULL && _strip(self->thin, self->codestr_ptr, NULL)) {
		self->init = self->thin;
	}
	self->thin = NULL;
	self->safe = self->codestr_ptr + 1;
}

static void
_BlockLocator_mark_thin(BlockLocator *self) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	// Step on thin ice, if it breaks, it breaks here
	if (self->thin != NULL && _strip(self->thin, self->codestr_ptr, NULL)) {
		self->init = self->thin;
		self->thin = self->codestr_ptr + 1;
	} else if (self->thin == NULL && _strip(self->safe, self->codestr_ptr, NULL)) {
		self->thin = self->codestr_ptr + 1;
	}
}

int function_map_initialized = 0;
_BlockLocator_Callback* scss_function_map[256 * 256 * 2 * 3]; // (c, instr, par, depth)

static void
init_function_map(void) {
	int i;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (function_map_initialized) {
		return;
	}
	function_map_initialized = 1;

	for (i = 0; i < 256 * 256 * 2 * 3; i++) {
		scss_function_map[i] = NULL;
	}
	scss_function_map[(int)'\"' + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_start_string;
	scss_function_map[(int)'\'' + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_start_string;
	scss_function_map[(int)'\"' + 256*0 + 256*256*1 + 256*256*2*0] = _BlockLocator_start_string;
	scss_function_map[(int)'\'' + 256*0 + 256*256*1 + 256*256*2*0] = _BlockLocator_start_string;
	scss_function_map[(int)'\"' + 256*0 + 256*256*0 + 256*256*2*1] = _BlockLocator_start_string;
	scss_function_map[(int)'\'' + 256*0 + 256*256*0 + 256*256*2*1] = _BlockLocator_start_string;
	scss_function_map[(int)'\"' + 256*0 + 256*256*1 + 256*256*2*1] = _BlockLocator_start_string;
	scss_function_map[(int)'\'' + 256*0 + 256*256*1 + 256*256*2*1] = _BlockLocator_start_string;
	scss_function_map[(int)'\"' + 256*0 + 256*256*0 + 256*256*2*2] = _BlockLocator_start_string;
	scss_function_map[(int)'\'' + 256*0 + 256*256*0 + 256*256*2*2] = _BlockLocator_start_string;
	scss_function_map[(int)'\"' + 256*0 + 256*256*1 + 256*256*2*2] = _BlockLocator_start_string;
	scss_function_map[(int)'\'' + 256*0 + 256*256*1 + 256*256*2*2] = _BlockLocator_start_string;

	scss_function_map[(int)'\"' + 256*(int)'\"' + 256*256*0 + 256*256*2*0] = _BlockLocator_end_string;
	scss_function_map[(int)'\'' + 256*(int)'\'' + 256*256*0 + 256*256*2*0] = _BlockLocator_end_string;
	scss_function_map[(int)'\"' + 256*(int)'\"' + 256*256*1 + 256*256*2*0] = _BlockLocator_end_string;
	scss_function_map[(int)'\'' + 256*(int)'\'' + 256*256*1 + 256*256*2*0] = _BlockLocator_end_string;
	scss_function_map[(int)'\"' + 256*(int)'\"' + 256*256*0 + 256*256*2*1] = _BlockLocator_end_string;
	scss_function_map[(int)'\'' + 256*(int)'\'' + 256*256*0 + 256*256*2*1] = _BlockLocator_end_string;
	scss_function_map[(int)'\"' + 256*(int)'\"' + 256*256*1 + 256*256*2*1] = _BlockLocator_end_string;
	scss_function_map[(int)'\'' + 256*(int)'\'' + 256*256*1 + 256*256*2*1] = _BlockLocator_end_string;
	scss_function_map[(int)'\"' + 256*(int)'\"' + 256*256*0 + 256*256*2*2] = _BlockLocator_end_string;
	scss_function_map[(int)'\'' + 256*(int)'\'' + 256*256*0 + 256*256*2*2] = _BlockLocator_end_string;
	scss_function_map[(int)'\"' + 256*(int)'\"' + 256*256*1 + 256*256*2*2] = _BlockLocator_end_string;
	scss_function_map[(int)'\'' + 256*(int)'\'' + 256*256*1 + 256*256*2*2] = _BlockLocator_end_string;

	scss_function_map[(int)'(' + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_start_parenthesis;
	scss_function_map[(int)'(' + 256*0 + 256*256*1 + 256*256*2*0] = _BlockLocator_start_parenthesis;
	scss_function_map[(int)'(' + 256*0 + 256*256*0 + 256*256*2*1] = _BlockLocator_start_parenthesis;
	scss_function_map[(int)'(' + 256*0 + 256*256*1 + 256*256*2*1] = _BlockLocator_start_parenthesis;
	scss_function_map[(int)'(' + 256*0 + 256*256*0 + 256*256*2*2] = _BlockLocator_start_parenthesis;
	scss_function_map[(int)'(' + 256*0 + 256*256*1 + 256*256*2*2] = _BlockLocator_start_parenthesis;

	scss_function_map[(int)')' + 256*0 + 256*256*1 + 256*256*2*0] = _BlockLocator_end_parenthesis;
	scss_function_map[(int)')' + 256*0 + 256*256*1 + 256*256*2*1] = _BlockLocator_end_parenthesis;
	scss_function_map[(int)')' + 256*0 + 256*256*1 + 256*256*2*2] = _BlockLocator_end_parenthesis;

	scss_function_map[(int)'{' + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_start_block1;
	scss_function_map[(int)'{' + 256*0 + 256*256*0 + 256*256*2*1] = _BlockLocator_start_block;
	scss_function_map[(int)'{' + 256*0 + 256*256*0 + 256*256*2*2] = _BlockLocator_start_block;

	scss_function_map[(int)'}' + 256*0 + 256*256*0 + 256*256*2*1] = _BlockLocator_end_block1;
	scss_function_map[(int)'}' + 256*0 + 256*256*0 + 256*256*2*2] = _BlockLocator_end_block;

	scss_function_map[(int)';' + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_end_property;

	scss_function_map[(int)',' + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_mark_safe;

	scss_function_map[(int)'\n' + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_mark_thin;

	scss_function_map[0 + 256*0 + 256*256*0 + 256*256*2*0] = _BlockLocator_flush_properties;
	scss_function_map[0 + 256*0 + 256*256*0 + 256*256*2*1] = _BlockLocator_flush_properties;
	scss_function_map[0 + 256*0 + 256*256*0 + 256*256*2*2] = _BlockLocator_flush_properties;

	#ifdef DEBUG
		fprintf(stderr, "\tScss function maps initialized!\n");
	#endif
}


/* BlockLocator public interface */

void
BlockLocator_initialize(void)
{
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	init_function_map();
}

void
BlockLocator_finalize(void)
{
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif
}

BlockLocator *
BlockLocator_new(char *codestr, int codestr_sz)
{
	BlockLocator *self;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	self = PyMem_New(BlockLocator, 1);
	if (self) {
		memset(self, 0, sizeof(BlockLocator));
		self->_codestr = PyMem_New(char, codestr_sz);
		memcpy(self->_codestr, codestr, codestr_sz);
		self->codestr_sz = codestr_sz;
		self->codestr = PyMem_New(char, self->codestr_sz);
		memcpy(self->codestr, self->_codestr, self->codestr_sz);
		self->codestr_ptr = self->codestr;
		self->lineno = 0;
		self->par = 0;
		self->instr = 0;
		self->depth = 0;
		self->skip = 0;
		self->thin = self->codestr;
		self->init = self->codestr;
		self->safe = self->codestr;
		self->lose = self->codestr;
		self->start = NULL;
		self->end = NULL;
		#ifdef DEBUG
			fprintf(stderr, "\tScss BlockLocator object created (%d bytes)!\n", codestr_sz);
		#endif
	}
	return self;
}

void
BlockLocator_del(BlockLocator *self)
{
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	free(self->codestr);
	free(self->_codestr);
	free(self);
}

void
BlockLocator_rewind(BlockLocator *self)
{
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	free(self->codestr);
	self->codestr = PyMem_New(char, self->codestr_sz);
	memcpy(self->codestr, self->_codestr, self->codestr_sz);
	self->codestr_ptr = self->codestr;
	self->lineno = 0;
	self->par = 0;
	self->instr = 0;
	self->depth = 0;
	self->skip = 0;
	self->thin = self->codestr;
	self->init = self->codestr;
	self->safe = self->codestr;
	self->lose = self->codestr;
	self->start = NULL;
	self->end = NULL;

	#ifdef DEBUG
		fprintf(stderr, "\tScss BlockLocator object rewound!\n");
	#endif
}

Block*
BlockLocator_iternext(BlockLocator *self)
{
	_BlockLocator_Callback *fn;
	unsigned char c = 0;
	char *codestr_end = self->codestr + self->codestr_sz;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	memset(&self->block, 0, sizeof(Block));

	while (self->codestr_ptr < codestr_end) {
		c = *(self->codestr_ptr);
		if (!c) {
			self->codestr_ptr++;
			continue;
		}

		repeat:

		fn = scss_function_map[
			(int)c +
			256 * self->instr +
			256 * 256 * (int)(self->par != 0) +
			256 * 256 * 2 * (int)(self->depth > 1 ? 2 : self->depth)
		];

		if (fn != NULL) {
			fn(self);
		}

		self->codestr_ptr++;
		if (self->codestr_ptr > codestr_end) {
			self->codestr_ptr = codestr_end;
		}

		if (self->block.error) {
			#ifdef DEBUG
				if (self->block.error > 0) {
					fprintf(stderr, "\tBlock found!\n");
				} else {
					fprintf(stderr, "\tException!\n");
				}
			#endif
			return &self->block;
		}
	}
	if (self->par > 0) {
		if (self->block.error >= 0) {
			self->block.error = -1;
			sprintf(self->exc, "Missing closing parenthesis somewhere in block");
			#ifdef DEBUG
				fprintf(stderr, "\t%s\n", self->exc);
			#endif
		}
	} else if (self->instr != 0) {
		if (self->block.error >= 0) {
			self->block.error = -2;
			sprintf(self->exc, "Missing closing string somewhere in block");
			#ifdef DEBUG
				fprintf(stderr, "\t%s\n", self->exc);
			#endif
		}
	} else if (self->depth > 0) {
		if (self->block.error >= 0) {
			self->block.error = -3;
			sprintf(self->exc, "Missing closing string somewhere in block");
			#ifdef DEBUG
				fprintf(stderr, "\t%s\n", self->exc);
			#endif
		}
		if (self->init < codestr_end) {
			c = '}';
			goto repeat;
		}
	}
	if (self->init < codestr_end) {
		self->init = codestr_end;
		c = 0;
		goto repeat;
	}

	BlockLocator_rewind(self);

	return &self->block;
}
