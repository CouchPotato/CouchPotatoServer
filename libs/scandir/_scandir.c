// scandir C speedups
//
// TODO: this is a work in progress!
//
// There's a fair bit of PY_MAJOR_VERSION boilerplate to support both Python 2
// and Python 3 -- the structure of this is taken from here:
// http://docs.python.org/3.3/howto/cporting.html

#include <Python.h>
#include <structseq.h>

#ifdef MS_WINDOWS
#include <windows.h>
#endif

#if PY_MAJOR_VERSION >= 3
#define INITERROR return NULL
#define FROM_LONG PyLong_FromLong
#define FROM_STRING PyUnicode_FromStringAndSize
#else
#define INITERROR return
#define FROM_LONG PyInt_FromLong
#define FROM_STRING PyString_FromStringAndSize
#endif

#ifdef MS_WINDOWS

static PyObject *
win32_error_unicode(char* function, Py_UNICODE* filename)
{
    errno = GetLastError();
    if (filename)
        return PyErr_SetFromWindowsErrWithUnicodeFilename(errno, filename);
    else
        return PyErr_SetFromWindowsErr(errno);
}

/* Below, we *know* that ugo+r is 0444 */
#if _S_IREAD != 0400
#error Unsupported C library
#endif
static int
attributes_to_mode(DWORD attr)
{
    int m = 0;
    if (attr & FILE_ATTRIBUTE_DIRECTORY)
        m |= _S_IFDIR | 0111; /* IFEXEC for user,group,other */
    else
        m |= _S_IFREG;
    if (attr & FILE_ATTRIBUTE_READONLY)
        m |= 0444;
    else
        m |= 0666;
    if (attr & FILE_ATTRIBUTE_REPARSE_POINT)
        m |= 0120000;  // S_IFLNK
    return m;
}

double
filetime_to_time(FILETIME *filetime)
{
    const double SECONDS_BETWEEN_EPOCHS = 11644473600.0;

    unsigned long long total = (unsigned long long)filetime->dwHighDateTime << 32 |
                               (unsigned long long)filetime->dwLowDateTime;
    return (double)total / 10000000.0 - SECONDS_BETWEEN_EPOCHS;
}

static PyTypeObject StatResultType;

static PyObject *
find_data_to_statresult(WIN32_FIND_DATAW *data)
{
    PY_LONG_LONG size;
    PyObject *v = PyStructSequence_New(&StatResultType);
    if (v == NULL)
        return NULL;

    size = (PY_LONG_LONG)data->nFileSizeHigh << 32 |
           (PY_LONG_LONG)data->nFileSizeLow;

    PyStructSequence_SET_ITEM(v, 0, FROM_LONG(attributes_to_mode(data->dwFileAttributes)));
    PyStructSequence_SET_ITEM(v, 1, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 2, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 3, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 4, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 5, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 6, PyLong_FromLongLong((PY_LONG_LONG)size));
    PyStructSequence_SET_ITEM(v, 7, PyFloat_FromDouble(filetime_to_time(&data->ftLastAccessTime)));
    PyStructSequence_SET_ITEM(v, 8, PyFloat_FromDouble(filetime_to_time(&data->ftLastWriteTime)));
    PyStructSequence_SET_ITEM(v, 9, PyFloat_FromDouble(filetime_to_time(&data->ftCreationTime)));

    if (PyErr_Occurred()) {
        Py_DECREF(v);
        return NULL;
    }

    return v;
}

static PyStructSequence_Field stat_result_fields[] = {
    {"st_mode",    "protection bits"},
    {"st_ino",     "inode"},
    {"st_dev",     "device"},
    {"st_nlink",   "number of hard links"},
    {"st_uid",     "user ID of owner"},
    {"st_gid",     "group ID of owner"},
    {"st_size",    "total size, in bytes"},
    {"st_atime",   "time of last access"},
    {"st_mtime",   "time of last modification"},
    {"st_ctime",   "time of last change"},
    {0}
};

static PyStructSequence_Desc stat_result_desc = {
    "stat_result", /* name */
    NULL, /* doc */
    stat_result_fields,
    10
};

static PyObject *
scandir_helper(PyObject *self, PyObject *args)
{
    PyObject *d, *v;
    HANDLE hFindFile;
    BOOL result;
    WIN32_FIND_DATAW wFileData;
    Py_UNICODE *wnamebuf;
    Py_ssize_t len;
    PyObject *po;
    PyObject *name_stat;

    if (!PyArg_ParseTuple(args, "U:scandir_helper", &po))
        return NULL;

    /* Overallocate for \\*.*\0 */
    len = PyUnicode_GET_SIZE(po);
    wnamebuf = malloc((len + 5) * sizeof(wchar_t));
    if (!wnamebuf) {
        PyErr_NoMemory();
        return NULL;
    }
    wcscpy(wnamebuf, PyUnicode_AS_UNICODE(po));
    if (len > 0) {
        Py_UNICODE wch = wnamebuf[len-1];
        if (wch != L'/' && wch != L'\\' && wch != L':')
            wnamebuf[len++] = L'\\';
        wcscpy(wnamebuf + len, L"*.*");
    }
    if ((d = PyList_New(0)) == NULL) {
        free(wnamebuf);
        return NULL;
    }
    Py_BEGIN_ALLOW_THREADS
    hFindFile = FindFirstFileW(wnamebuf, &wFileData);
    Py_END_ALLOW_THREADS
    if (hFindFile == INVALID_HANDLE_VALUE) {
        int error = GetLastError();
        if (error == ERROR_FILE_NOT_FOUND) {
            free(wnamebuf);
            return d;
        }
        Py_DECREF(d);
        win32_error_unicode("FindFirstFileW", wnamebuf);
        free(wnamebuf);
        return NULL;
    }
    do {
        /* Skip over . and .. */
        if (wcscmp(wFileData.cFileName, L".") != 0 &&
            wcscmp(wFileData.cFileName, L"..") != 0) {
            v = PyUnicode_FromUnicode(wFileData.cFileName, wcslen(wFileData.cFileName));
            if (v == NULL) {
                Py_DECREF(d);
                d = NULL;
                break;
            }
            name_stat = Py_BuildValue("ON", v, find_data_to_statresult(&wFileData));
            if (name_stat == NULL) {
                Py_DECREF(v);
                Py_DECREF(d);
                d = NULL;
                break;
            }
            if (PyList_Append(d, name_stat) != 0) {
                Py_DECREF(v);
                Py_DECREF(d);
                Py_DECREF(name_stat);
                d = NULL;
                break;
            }
            Py_DECREF(name_stat);
            Py_DECREF(v);
        }
        Py_BEGIN_ALLOW_THREADS
        result = FindNextFileW(hFindFile, &wFileData);
        Py_END_ALLOW_THREADS
        /* FindNextFile sets error to ERROR_NO_MORE_FILES if
           it got to the end of the directory. */
        if (!result && GetLastError() != ERROR_NO_MORE_FILES) {
            Py_DECREF(d);
            win32_error_unicode("FindNextFileW", wnamebuf);
            FindClose(hFindFile);
            free(wnamebuf);
            return NULL;
        }
    } while (result == TRUE);

    if (FindClose(hFindFile) == FALSE) {
        Py_DECREF(d);
        win32_error_unicode("FindClose", wnamebuf);
        free(wnamebuf);
        return NULL;
    }
    free(wnamebuf);
    return d;
}

#else  // Linux / OS X

#include <dirent.h>
#define NAMLEN(dirent) strlen((dirent)->d_name)

static PyObject *
posix_error_with_allocated_filename(char* name)
{
    PyObject *rc = PyErr_SetFromErrnoWithFilename(PyExc_OSError, name);
    PyMem_Free(name);
    return rc;
}

static PyObject *
scandir_helper(PyObject *self, PyObject *args)
{
    char *name = NULL;
    PyObject *d, *v, *name_type;
    DIR *dirp;
    struct dirent *ep;
    int arg_is_unicode = 1;

    errno = 0;
    if (!PyArg_ParseTuple(args, "U:scandir_helper", &v)) {
        arg_is_unicode = 0;
        PyErr_Clear();
    }
    if (!PyArg_ParseTuple(args, "et:scandir_helper", Py_FileSystemDefaultEncoding, &name))
        return NULL;
    Py_BEGIN_ALLOW_THREADS
    dirp = opendir(name);
    Py_END_ALLOW_THREADS
    if (dirp == NULL) {
        return posix_error_with_allocated_filename(name);
    }
    if ((d = PyList_New(0)) == NULL) {
        Py_BEGIN_ALLOW_THREADS
        closedir(dirp);
        Py_END_ALLOW_THREADS
        PyMem_Free(name);
        return NULL;
    }
    for (;;) {
        errno = 0;
        Py_BEGIN_ALLOW_THREADS
        ep = readdir(dirp);
        Py_END_ALLOW_THREADS
        if (ep == NULL) {
            if (errno == 0) {
                break;
            } else {
                Py_BEGIN_ALLOW_THREADS
                closedir(dirp);
                Py_END_ALLOW_THREADS
                Py_DECREF(d);
                return posix_error_with_allocated_filename(name);
            }
        }
        if (ep->d_name[0] == '.' &&
            (NAMLEN(ep) == 1 ||
             (ep->d_name[1] == '.' && NAMLEN(ep) == 2)))
            continue;
        v = FROM_STRING(ep->d_name, NAMLEN(ep));
        if (v == NULL) {
            Py_DECREF(d);
            d = NULL;
            break;
        }
        if (arg_is_unicode) {
            PyObject *w;

            w = PyUnicode_FromEncodedObject(v,
                                            Py_FileSystemDefaultEncoding,
                                            "strict");
            if (w != NULL) {
                Py_DECREF(v);
                v = w;
            }
            else {
                /* fall back to the original byte string, as
                   discussed in patch #683592 */
                PyErr_Clear();
            }
        }
        name_type = Py_BuildValue("ON", v, FROM_LONG(ep->d_type));
        if (name_type == NULL) {
            Py_DECREF(v);
            Py_DECREF(d);
            d = NULL;
            break;
        }
        if (PyList_Append(d, name_type) != 0) {
            Py_DECREF(v);
            Py_DECREF(d);
            Py_DECREF(name_type);
            d = NULL;
            break;
        }
        Py_DECREF(name_type);
        Py_DECREF(v);
    }
    Py_BEGIN_ALLOW_THREADS
    closedir(dirp);
    Py_END_ALLOW_THREADS
    PyMem_Free(name);

    return d;
}

#endif

static PyMethodDef scandir_methods[] = {
    {"scandir_helper", (PyCFunction)scandir_helper, METH_VARARGS, NULL},
    {NULL, NULL},
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_scandir",
        NULL,
        0,
        scandir_methods,
        NULL,
        NULL,
        NULL,
        NULL,
};
#endif

#if PY_MAJOR_VERSION >= 3
PyObject *
PyInit__scandir(void)
{
    PyObject *module = PyModule_Create(&moduledef);
#else
void
init_scandir(void)
{
    PyObject *module = Py_InitModule("_scandir", scandir_methods);
#endif
    if (module == NULL) {
        INITERROR;
    }

#ifdef MS_WINDOWS
    stat_result_desc.name = "scandir.stat_result";
    PyStructSequence_InitType(&StatResultType, &stat_result_desc);
#endif

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
