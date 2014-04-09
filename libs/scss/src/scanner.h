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
#ifndef SCANNER_H
#define SCANNER_H

#define PCRE_STATIC
#include <pcre.h>

#define BLOCK_SIZE_PATTERNS 50
#define BLOCK_SIZE_TOKENS 50

#define MAX_EXC_STRING 4096

#define SCANNER_EXC_BAD_TOKEN (long)-1
#define SCANNER_EXC_RESTRICTED (long)-2
#define SCANNER_EXC_UNIMPLEMENTED (long)-3
#define SCANNER_EXC_NO_MORE_TOKENS (long)-4

typedef struct {
	char *tok;
	char *expr;
	pcre *pattern;
} Pattern;

typedef struct {
	Pattern *regex;
	char *string;
	int string_sz;
} Token;

typedef struct {
	int patterns_sz;
	Pattern **patterns;
} Restriction;

typedef struct {
	char exc[MAX_EXC_STRING];
    int ignore_sz;
    Pattern **ignore;
    int tokens_sz;
    int tokens_bsz;
    Token *tokens;
    Restriction *restrictions;
    int input_sz;
    char *input;
	int pos;
} Scanner;

int Scanner_initialized(void);
void Scanner_initialize(Pattern *, int);
void Scanner_finalize(void);

void Scanner_reset(Scanner *self, char *input, int input_sz);
Scanner *Scanner_new(Pattern *, int, Pattern *, int, char *, int);
void Scanner_del(Scanner *);

Token* Scanner_token(Scanner *, int, Pattern *, int);
void Scanner_rewind(Scanner *, int);

#endif
