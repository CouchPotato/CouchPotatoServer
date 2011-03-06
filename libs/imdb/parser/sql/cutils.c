/*
 * cutils.c module.
 *
 * Miscellaneous functions to speed up the IMDbPY package.
 *
 * Contents:
 * - pyratcliff():
 *   Function that implements the Ratcliff-Obershelp comparison
 *   amongst Python strings.
 *
 * - pysoundex():
 *   Return a soundex code string, for the given string.
 *
 * Copyright 2004-2009 Davide Alberani <da@erlug.linux.it>
 * Released under the GPL license.
 *
 * NOTE: The Ratcliff-Obershelp part was heavily based on code from the
 * "simil" Python module.
 * The "simil" module is copyright of Luca Montecchiani <cbm64 _at_ inwind.it>
 * and can be found here: http://spazioinwind.libero.it/montecchiani/
 * It was released under the GPL license; original comments are leaved
 * below.
 *
 */


/*========== Ratcliff-Obershelp ==========*/
/*****************************************************************************
 *
 * Stolen code from :
 *
 * [Python-Dev] Why is soundex marked obsolete?
 * by Eric S. Raymond [4]esr@thyrsus.com
 * on Sun, 14 Jan 2001 14:09:01 -0500
 *
 *****************************************************************************/

/*****************************************************************************
 *
 * Ratcliff-Obershelp common-subpattern similarity.
 *
 * This code first appeared in a letter to the editor in Doctor
 * Dobbs's Journal, 11/1988.  The original article on the algorithm,
 * "Pattern Matching by Gestalt" by John Ratcliff, had appeared in the
 * July 1988 issue (#181) but the algorithm was presented in assembly.
 * The main drawback of the Ratcliff-Obershelp algorithm is the cost
 * of the pairwise comparisons.  It is significantly more expensive
 * than stemming, Hamming distance, soundex, and the like.
 *
 * Running time quadratic in the data size, memory usage constant.
 *
 *****************************************************************************/

#include <Python.h>

#define DONTCOMPARE_NULL    0.0
#define DONTCOMPARE_SAME    1.0
#define COMPARE             2.0
#define STRING_MAXLENDIFFER 0.7

/* As of 05 Mar 2008, the longest title is ~600 chars. */
#define MXLINELEN   1023

#define MAX(a,b) ((a) > (b) ? (a) : (b))


//*****************************************
// preliminary check....
//*****************************************
static float
strings_check(char const *s, char const *t)
{
    float threshold;    // lenght difference
    int s_len = strlen(s);    // length of s
    int t_len = strlen(t);    // length of t

    // NULL strings ?
    if ((t_len * s_len) == 0)
        return (DONTCOMPARE_NULL);

    // the same ?
    if (strcmp(s, t) == 0)
        return (DONTCOMPARE_SAME);

    // string lenght difference threshold
    // we don't want to compare too different lenght strings ;)
    if (s_len < t_len)
        threshold = (float) s_len / (float) t_len;
    else
        threshold = (float) t_len / (float) s_len;
    if (threshold < STRING_MAXLENDIFFER)
        return (DONTCOMPARE_NULL);

    // proceed
    return (COMPARE);
}


static int
RatcliffObershelp(char *st1, char *end1, char *st2, char *end2)
{
    register char *a1, *a2;
    char *b1, *b2;
    char *s1 = st1, *s2 = st2;    /* initializations are just to pacify GCC */
    short max, i;

    if (end1 <= st1 || end2 <= st2)
        return (0);
    if (end1 == st1 + 1 && end2 == st2 + 1)
        return (0);

    max = 0;
    b1 = end1;
    b2 = end2;

    for (a1 = st1; a1 < b1; a1++) {
        for (a2 = st2; a2 < b2; a2++) {
            if (*a1 == *a2) {
                /* determine length of common substring */
                for (i = 1; a1[i] && (a1[i] == a2[i]); i++)
                    continue;
                if (i > max) {
                    max = i;
                    s1 = a1;
                    s2 = a2;
                    b1 = end1 - max;
                    b2 = end2 - max;
                }
            }
        }
    }
    if (!max)
        return (0);
    max += RatcliffObershelp(s1 + max, end1, s2 + max, end2);    /* rhs */
    max += RatcliffObershelp(st1, s1, st2, s2);    /* lhs */
    return max;
}


static float
ratcliff(char *s1, char *s2)
/* compute Ratcliff-Obershelp similarity of two strings */
{
    int l1, l2;
    float res;

    // preliminary tests
    res = strings_check(s1, s2);
    if (res != COMPARE)
        return(res);

    l1 = strlen(s1);
    l2 = strlen(s2);

    return 2.0 * RatcliffObershelp(s1, s1 + l1, s2, s2 + l2) / (l1 + l2);
}


/* Change a string to lowercase. */
static void
strtolower(char *s1)
{
    int i;
    for (i=0; i < strlen(s1); i++) s1[i] = tolower(s1[i]);
}


/* Ratcliff-Obershelp for two python strings; returns a python float. */
static PyObject*
pyratcliff(PyObject *self, PyObject *pArgs)
{
    char *s1 = NULL;
    char *s2 = NULL;
    PyObject *discard = NULL;
    char s1copy[MXLINELEN+1];
    char s2copy[MXLINELEN+1];

    /* The optional PyObject parameter is here to be compatible
     * with the pure python implementation, which uses a
     * difflib.SequenceMatcher object. */
    if (!PyArg_ParseTuple(pArgs, "ss|O", &s1, &s2, &discard))
        return NULL;

    strncpy(s1copy, s1, MXLINELEN);
    strncpy(s2copy, s2, MXLINELEN);
    /* Work on copies. */
    strtolower(s1copy);
    strtolower(s2copy);

    return Py_BuildValue("f", ratcliff(s1copy, s2copy));
}


/*========== soundex ==========*/
/* Max length of the soundex code to output (an uppercase char and
 * _at most_ 4 digits). */
#define SOUNDEX_LEN 5

/* Group Number Lookup Table  */
static char soundTable[26] =
{ 0 /* A */, '1' /* B */, '2' /* C */, '3' /* D */, 0 /* E */, '1' /* F */,
 '2' /* G */, 0 /* H */, 0 /* I */, '2' /* J */, '2' /* K */, '4' /* L */,
 '5' /* M */, '5' /* N */, 0 /* O */, '1' /* P */, '2' /* Q */, '6' /* R */,
 '2' /* S */, '3' /* T */, 0 /* U */, '1' /* V */, 0 /* W */, '2' /* X */,
  0 /* Y */, '2' /* Z */};

static PyObject*
pysoundex(PyObject *self, PyObject *pArgs)
{
    int i, j, n;
    char *s = NULL;
    char word[MXLINELEN+1];
    char soundCode[SOUNDEX_LEN+1];
    char c;

    if (!PyArg_ParseTuple(pArgs, "s", &s))
        return NULL;

    j = 0;
    n = strlen(s);

    /* Convert to uppercase and exclude non-ascii chars. */
    for (i = 0; i < n; i++) {
        c = toupper(s[i]);
        if (c < 91 && c > 64) {
            word[j] = c;
            j++;
        }
    }
    word[j] = '\0';

    n = strlen(word);
    if (n == 0) {
        /* If the string is empty, returns None. */
        return Py_BuildValue("");
    }
    soundCode[0] = word[0];

    /* Build the soundCode string. */
    j = 1;
    for (i = 1; j < SOUNDEX_LEN && i < n; i++) {
        c = soundTable[(word[i]-65)];
        /* Compact zeroes and equal consecutive digits ("12234112"->"123412") */
        if (c != 0 && c != soundCode[j-1]) {
                soundCode[j++] = c;
        }
    }
    soundCode[j] = '\0';

    return Py_BuildValue("s", soundCode);
}


static PyMethodDef cutils_methods[] = {
    {"ratcliff", pyratcliff,
        METH_VARARGS, "Ratcliff-Obershelp similarity."},
    {"soundex", pysoundex,
        METH_VARARGS, "Soundex code for strings."},
    {NULL}
};


void
initcutils(void)
{
    Py_InitModule("cutils", cutils_methods);
}


