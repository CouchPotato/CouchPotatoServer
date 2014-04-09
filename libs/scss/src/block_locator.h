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
#ifndef BLOCK_LOCATOR_H
#define BLOCK_LOCATOR_H

#define MAX_EXC_STRING 4096

typedef struct {
    int error;
    int lineno;
    char *selprop;
    int selprop_sz;
    char *codestr;
    int codestr_sz;
} Block;

typedef struct {
    char exc[MAX_EXC_STRING];
    char *_codestr;
    char *codestr;
    char *codestr_ptr;
    int codestr_sz;
    int lineno;
    int par;
    char instr;
    int depth;
    int skip;
    char *thin;
    char *init;
    char *safe;
    char *lose;
    char *start;
    char *end;
    Block block;
} BlockLocator;

void BlockLocator_initialize(void);
void BlockLocator_finalize(void);

Block* BlockLocator_iternext(BlockLocator *self);
BlockLocator *BlockLocator_new(char *codestr, int codestr_sz);
void BlockLocator_del(BlockLocator *self);

#endif
