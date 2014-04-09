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
#include <string.h>
#include "scanner.h"

#include "utils.h"

int Pattern_patterns_sz = 0;
int Pattern_patterns_bsz = 0;
Pattern *Pattern_patterns = NULL;
int Pattern_patterns_initialized = 0;

Pattern*
Pattern_regex(char *tok, char *expr) {
	int j;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	for (j = 0; j < Pattern_patterns_sz; j++) {
		if (strcmp(Pattern_patterns[j].tok, tok) == 0) {
			return &Pattern_patterns[j];
		}
	}
	if (expr) {
		if (j >= Pattern_patterns_bsz) {
			/* Needs to expand block */
			Pattern_patterns_bsz = Pattern_patterns_bsz + BLOCK_SIZE_PATTERNS;
			PyMem_Resize(Pattern_patterns, Pattern, Pattern_patterns_bsz);
		}
		Pattern_patterns[j].tok = PyMem_Strdup(tok);
		Pattern_patterns[j].expr = PyMem_Strdup(expr);
		Pattern_patterns[j].pattern = NULL;
		Pattern_patterns_sz = j + 1;
		return &Pattern_patterns[j];
	}
	return NULL;
}

static int
Pattern_match(Pattern *regex, char *string, int string_sz, int start_at, Token *p_token) {
	int options = PCRE_ANCHORED;
	const char *errptr;
	int ret, erroffset, ovector[3];
	pcre *p_pattern = regex->pattern;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (p_pattern == NULL) {
		#ifdef DEBUG
			fprintf(stderr, "\tpcre_compile %s\n", repr(regex->expr));
		#endif
		p_pattern = regex->pattern = pcre_compile(regex->expr, options, &errptr, &erroffset, NULL);
	}
	ret = pcre_exec(
		p_pattern,
		NULL,                  /* no extra data */
		string,
		string_sz,
		start_at,
		PCRE_ANCHORED,         /* default options */
		ovector,               /* output vector for substring information */
		3                      /* number of elements in the output vector */
	);
	if (ret >= 0) {
		if (p_token) {
			p_token->regex = regex;
			p_token->string = string + ovector[0];
			p_token->string_sz = ovector[1] - ovector[0];
		}
		return 1;
	}
	return 0;
}

static void Pattern_initialize(Pattern *, int);
static void Pattern_setup(Pattern *, int);
static void Pattern_finalize(void);


static void
Pattern_initialize(Pattern *patterns, int patterns_sz) {
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (!Pattern_patterns_initialized) {
		if (patterns_sz) {
			Pattern_patterns_initialized = 1;
			Pattern_setup(patterns, patterns_sz);
		}
	}
}

static void
Pattern_setup(Pattern *patterns, int patterns_sz) {
	int i;
	Pattern *regex;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (!Pattern_patterns_initialized) {
		Pattern_initialize(patterns, patterns_sz);
	} else {
		for (i = 0; i < patterns_sz; i++) {
			regex = Pattern_regex(patterns[i].tok, patterns[i].expr);
			#ifdef DEBUG
			if (regex) {
				fprintf(stderr, "\tAdded regex pattern %s: %s\n", repr(regex->tok), repr(regex->expr));
			}
			#endif
		}
	}
}

static void
Pattern_finalize(void) {
	int j;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (Pattern_patterns_initialized) {
		for (j = 0; j < Pattern_patterns_sz; j++) {
			PyMem_Del(Pattern_patterns[j].tok);
			PyMem_Del(Pattern_patterns[j].expr);
			if (Pattern_patterns[j].pattern != NULL) {
				pcre_free(Pattern_patterns[j].pattern);
			}
		}
		PyMem_Del(Pattern_patterns);
		Pattern_patterns = NULL;
		Pattern_patterns_sz = 0;
		Pattern_patterns_bsz = 0;
		Pattern_patterns_initialized = 0;
	}
}

/* Scanner */


static long
_Scanner_scan(Scanner *self, Pattern *restrictions, int restrictions_sz)
{
	Token best_token, *p_token;
	Restriction *p_restriction;
	Pattern *regex;
	int j, k, max, skip;
	size_t len;
	char *aux;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	while (1) {
		regex = NULL;
		best_token.regex = NULL;
		/* Search the patterns for a match, with earlier
		   tokens in the list having preference */
		for (j = 0; j < Pattern_patterns_sz; j++) {
			regex = &Pattern_patterns[j];
			#ifdef DEBUG
				fprintf(stderr, "\tTrying %s: %s at pos %d -> %s\n", repr(regex->tok), repr(regex->expr), self->pos, repr(self->input));
			#endif
			/* First check to see if we're restricting to this token */
			skip = restrictions_sz;
			if (skip) {
				max = (restrictions_sz > self->ignore_sz) ? restrictions_sz : self->ignore_sz;
				for (k = 0; k < max; k++) {
					if (k < restrictions_sz && strcmp(regex->tok, restrictions[k].tok) == 0) {
						skip = 0;
						break;
					}
					if (k < self->ignore_sz && regex == self->ignore[k]) {
						skip = 0;
						break;
					}
				}
				if (skip) {
					continue;
					#ifdef DEBUG
						fprintf(stderr, "\tSkipping %s!\n", repr(regex->tok));
					#endif
				}
			}
			if (Pattern_match(
				regex,
				self->input,
				self->input_sz,
				self->pos,
				&best_token
			)) {
				#ifdef DEBUG
					fprintf(stderr, "Match OK! %s: %s at pos %d\n", repr(regex->tok), repr(regex->expr), self->pos);
				#endif
				break;
			}
		}
		/* If we didn't find anything, raise an error */
		if (best_token.regex == NULL) {
			if (restrictions_sz) {
				sprintf(self->exc, "SyntaxError[@ char %d: Bad token found while trying to find one of the restricted tokens: ", self->pos);
				aux = self->exc + strlen(self->exc);
				for (k=0; k<restrictions_sz; k++) {
					len = strlen(restrictions[k].tok);
					if (aux + len > self->exc + sizeof(self->exc) - 10) {
						sprintf(aux, (k > 0) ? ", ..." : "...");
						break;
					}
					sprintf(aux, (k > 0) ? ", %s" : "%s", repr(restrictions[k].tok));
					aux += len + 2;
				}
				sprintf(aux, "]");
				return SCANNER_EXC_RESTRICTED;
			}
			sprintf(self->exc, "SyntaxError[@ char %d: Bad token found]", self->pos);
			return SCANNER_EXC_BAD_TOKEN;
		}
		/* If we found something that isn't to be ignored, return it */
		skip = 0;
		for (k = 0; k < self->ignore_sz; k++) {
			if (best_token.regex == self->ignore[k]) {
				/* This token should be ignored... */
				self->pos += best_token.string_sz;
				skip = 1;
				break;
			}
		}
		if (!skip) {
			break;
		}
	}
	if (best_token.regex) {
		self->pos = (int)(best_token.string - self->input + best_token.string_sz);
		/* Only add this token if it's not in the list (to prevent looping) */
		p_token = &self->tokens[self->tokens_sz - 1];
		if (self->tokens_sz == 0 ||
			p_token->regex != best_token.regex ||
			p_token->string != best_token.string ||
			p_token->string_sz != best_token.string_sz
		) {
			if (self->tokens_sz >= self->tokens_bsz) {
				/* Needs to expand block */
				self->tokens_bsz = self->tokens_bsz + BLOCK_SIZE_PATTERNS;
				PyMem_Resize(self->tokens, Token, self->tokens_bsz);
				PyMem_Resize(self->restrictions, Restriction, self->tokens_bsz);
			}
			memcpy(&self->tokens[self->tokens_sz], &best_token, sizeof(Token));
			p_restriction = &self->restrictions[self->tokens_sz];
			if (restrictions_sz) {
				p_restriction->patterns = PyMem_New(Pattern *, restrictions_sz);
				p_restriction->patterns_sz = 0;
				for (j = 0; j < restrictions_sz; j++) {
					regex = Pattern_regex(restrictions[j].tok, restrictions[j].expr);
					if (regex) {
						p_restriction->patterns[p_restriction->patterns_sz++] = regex;
					}
				}
			} else {
				p_restriction->patterns = NULL;
				p_restriction->patterns_sz = 0;
			}
			self->tokens_sz++;
			return 1;
		}
	}
	return 0;
}


/* Scanner public interface */

void
Scanner_reset(Scanner *self, char *input, int input_sz) {
	int i;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	for (i = 0; i < self->tokens_sz; i++) {
		PyMem_Del(self->restrictions[i].patterns);
		self->restrictions[i].patterns = NULL;
		self->restrictions[i].patterns_sz = 0;
	}
	self->tokens_sz = 0;

	if (self->input != NULL) {
		PyMem_Del(self->input);
	}
	self->input = PyMem_Strndup(input, input_sz);
	self->input_sz = input_sz;
	#ifdef DEBUG
		fprintf(stderr, "Scanning in %s\n", repr(self->input));
	#endif

	self->pos = 0;
}

void
Scanner_del(Scanner *self) {
	int i;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (self->ignore != NULL) {
		PyMem_Del(self->ignore);
	}

	if (self->tokens != NULL) {
		for (i = 0; i < self->tokens_sz; i++) {
			PyMem_Del(self->restrictions[i].patterns);
		}
		PyMem_Del(self->tokens);
		PyMem_Del(self->restrictions);
	}

	if (self->input != NULL) {
		PyMem_Del(self->input);
	}

	PyMem_Del(self);
}

Scanner*
Scanner_new(Pattern patterns[], int patterns_sz, Pattern ignore[], int ignore_sz, char *input, int input_sz)
{
	int i;
	Scanner *self;
	Pattern *regex;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	self = PyMem_New(Scanner, 1);
	memset(self, 0, sizeof(Scanner));
	if (self) {
		for (i = 0; i < patterns_sz; i++) {
			regex = Pattern_regex(patterns[i].tok, patterns[i].expr);
			#ifdef DEBUG
			if (regex) {
				fprintf(stderr, "\tAdded regex pattern %s: %s\n", repr(regex->tok), repr(regex->expr));
			}
			#endif
		}
		if (ignore_sz) {
			self->ignore = PyMem_New(Pattern *, ignore_sz);
			for (i = 0; i < ignore_sz; i++) {
				regex = Pattern_regex(ignore[i].tok, ignore[i].expr);
				if (regex) {
					self->ignore[self->ignore_sz++] = regex;
					#ifdef DEBUG
						fprintf(stderr, "\tIgnoring token %s\n", repr(regex->tok));
					#endif
				}
			}
		} else {
			self->ignore = NULL;
		}
		Scanner_reset(self, input, input_sz);
	}
	return self;
}

int
Scanner_initialized(void)
{
	return Pattern_patterns_initialized;
}

void
Scanner_initialize(Pattern patterns[], int patterns_sz)
{
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	Pattern_initialize(patterns, patterns_sz);
}

void
Scanner_finalize(void)
{
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	Pattern_finalize();
}

Token*
Scanner_token(Scanner *self, int i, Pattern restrictions[], int restrictions_sz)
{
	int j, k, found;
	Pattern *regex;
	long result;

	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (i == self->tokens_sz) {
		result = _Scanner_scan(self, restrictions, restrictions_sz);
		if (result < 0) {
			return (Token *)result;
		}
	} else if (i >= 0 && i < self->tokens_sz) {
		if (self->restrictions[i].patterns_sz) {
			for (j = 0; j < restrictions_sz; j++) {
				found = 0;
				for (k = 0; k < self->restrictions[i].patterns_sz; k++) {
					regex = Pattern_regex(restrictions[j].tok, restrictions[j].expr);
					if (strcmp(restrictions[j].tok, self->restrictions[i].patterns[k]->tok) == 0) {
						found = 1;
						break;
					}
				}
				if (!found) {
					sprintf(self->exc, "Unimplemented: restriction set changed");
					return (Token *)SCANNER_EXC_UNIMPLEMENTED;
				}
			}
		}
	}
	if (i >= 0 && i < self->tokens_sz) {
		return &self->tokens[i];
	}
	return (Token *)SCANNER_EXC_NO_MORE_TOKENS;
}

void
Scanner_rewind(Scanner *self, int i)
{
	#ifdef DEBUG
		fprintf(stderr, "%s\n", __PRETTY_FUNCTION__);
	#endif

	if (i >= 0 && i < self->tokens_sz) {
		self->tokens_sz = i;
		self->pos = (int)(self->tokens[i].string - self->input);
	}
}
