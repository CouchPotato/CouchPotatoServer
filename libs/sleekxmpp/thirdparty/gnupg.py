""" A wrapper for the 'gpg' command::

Portions of this module are derived from A.M. Kuchling's well-designed
GPG.py, using Richard Jones' updated version 1.3, which can be found
in the pycrypto CVS repository on Sourceforge:

http://pycrypto.cvs.sourceforge.net/viewvc/pycrypto/gpg/GPG.py

This module is *not* forward-compatible with amk's; some of the
old interface has changed.  For instance, since I've added decrypt
functionality, I elected to initialize with a 'gnupghome' argument
instead of 'keyring', so that gpg can find both the public and secret
keyrings.  I've also altered some of the returned objects in order for
the caller to not have to know as much about the internals of the
result classes.

While the rest of ISconf is released under the GPL, I am releasing
this single file under the same terms that A.M. Kuchling used for
pycrypto.

Steve Traugott, stevegt@terraluna.org
Thu Jun 23 21:27:20 PDT 2005

This version of the module has been modified from Steve Traugott's version
(see http://trac.t7a.org/isconf/browser/trunk/lib/python/isconf/GPG.py) by
Vinay Sajip to make use of the subprocess module (Steve's version uses os.fork()
and so does not work on Windows). Renamed to gnupg.py to avoid confusion with
the previous versions.

Modifications Copyright (C) 2008-2012 Vinay Sajip. All rights reserved.

A unittest harness (test_gnupg.py) has also been added.
"""
import locale

__version__ = "0.2.9"
__author__ = "Vinay Sajip"
__date__  = "$29-Mar-2012 21:12:58$"

try:
    from io import StringIO
except ImportError:
    from cStringIO import StringIO

import codecs
import locale
import logging
import os
import socket
from subprocess import Popen
from subprocess import PIPE
import sys
import threading

try:
    import logging.NullHandler as NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def handle(self, record):
            pass
try:
    unicode
    _py3k = False
except NameError:
    _py3k = True

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(NullHandler())

def _copy_data(instream, outstream):
    # Copy one stream to another
    sent = 0
    if hasattr(sys.stdin, 'encoding'):
        enc = sys.stdin.encoding
    else:
        enc = 'ascii'
    while True:
        data = instream.read(1024)
        if len(data) == 0:
            break
        sent += len(data)
        logger.debug("sending chunk (%d): %r", sent, data[:256])
        try:
            outstream.write(data)
        except UnicodeError:
            outstream.write(data.encode(enc))
        except:
            # Can sometimes get 'broken pipe' errors even when the data has all
            # been sent
            logger.exception('Error sending data')
            break
    try:
        outstream.close()
    except IOError:
        logger.warning('Exception occurred while closing: ignored', exc_info=1)
    logger.debug("closed output, %d bytes sent", sent)

def _threaded_copy_data(instream, outstream):
    wr = threading.Thread(target=_copy_data, args=(instream, outstream))
    wr.setDaemon(True)
    logger.debug('data copier: %r, %r, %r', wr, instream, outstream)
    wr.start()
    return wr

def _write_passphrase(stream, passphrase, encoding):
    passphrase = '%s\n' % passphrase
    passphrase = passphrase.encode(encoding)
    stream.write(passphrase)
    logger.debug("Wrote passphrase: %r", passphrase)

def _is_sequence(instance):
    return isinstance(instance,list) or isinstance(instance,tuple)

def _make_binary_stream(s, encoding):
    try:
        if _py3k:
            if isinstance(s, str):
                s = s.encode(encoding)
        else:
            if type(s) is not str:
                s = s.encode(encoding)
        from io import BytesIO
        rv = BytesIO(s)
    except ImportError:
        rv = StringIO(s)
    return rv

class Verify(object):
    "Handle status messages for --verify"

    def __init__(self, gpg):
        self.gpg = gpg
        self.valid = False
        self.fingerprint = self.creation_date = self.timestamp = None
        self.signature_id = self.key_id = None
        self.username = None

    def __nonzero__(self):
        return self.valid

    __bool__ = __nonzero__

    def handle_status(self, key, value):
        if key in ("TRUST_UNDEFINED", "TRUST_NEVER", "TRUST_MARGINAL",
                   "TRUST_FULLY", "TRUST_ULTIMATE", "RSA_OR_IDEA", "NODATA",
                   "IMPORT_RES", "PLAINTEXT", "PLAINTEXT_LENGTH",
                   "POLICY_URL", "DECRYPTION_INFO", "DECRYPTION_OKAY", "IMPORTED"):
            pass
        elif key == "BADSIG":
            self.valid = False
            self.status = 'signature bad'
            self.key_id, self.username = value.split(None, 1)
        elif key == "GOODSIG":
            self.valid = True
            self.status = 'signature good'
            self.key_id, self.username = value.split(None, 1)
        elif key == "VALIDSIG":
            (self.fingerprint,
             self.creation_date,
             self.sig_timestamp,
             self.expire_timestamp) = value.split()[:4]
            # may be different if signature is made with a subkey
            self.pubkey_fingerprint = value.split()[-1]
            self.status = 'signature valid'
        elif key == "SIG_ID":
            (self.signature_id,
             self.creation_date, self.timestamp) = value.split()
        elif key == "ERRSIG":
            self.valid = False
            (self.key_id,
             algo, hash_algo,
             cls,
             self.timestamp) = value.split()[:5]
            self.status = 'signature error'
        elif key == "DECRYPTION_FAILED":
            self.valid = False
            self.key_id = value
            self.status = 'decryption failed'
        elif key == "NO_PUBKEY":
            self.valid = False
            self.key_id = value
            self.status = 'no public key'
        elif key in ("KEYEXPIRED", "SIGEXPIRED"):
            # these are useless in verify, since they are spit out for any
            # pub/subkeys on the key, not just the one doing the signing.
            # if we want to check for signatures with expired key,
            # the relevant flag is EXPKEYSIG.
            pass
        elif key in ("EXPKEYSIG", "REVKEYSIG"):
            # signed with expired or revoked key
            self.valid = False
            self.key_id = value.split()[0]
            self.status = (('%s %s') % (key[:3], key[3:])).lower()
        else:
            raise ValueError("Unknown status message: %r" % key)

class ImportResult(object):
    "Handle status messages for --import"

    counts = '''count no_user_id imported imported_rsa unchanged
            n_uids n_subk n_sigs n_revoc sec_read sec_imported
            sec_dups not_imported'''.split()
    def __init__(self, gpg):
        self.gpg = gpg
        self.imported = []
        self.results = []
        self.fingerprints = []
        for result in self.counts:
            setattr(self, result, None)

    def __nonzero__(self):
        if self.not_imported: return False
        if not self.fingerprints: return False
        return True

    __bool__ = __nonzero__

    ok_reason = {
        '0': 'Not actually changed',
        '1': 'Entirely new key',
        '2': 'New user IDs',
        '4': 'New signatures',
        '8': 'New subkeys',
        '16': 'Contains private key',
    }

    problem_reason = {
        '0': 'No specific reason given',
        '1': 'Invalid Certificate',
        '2': 'Issuer Certificate missing',
        '3': 'Certificate Chain too long',
        '4': 'Error storing certificate',
    }

    def handle_status(self, key, value):
        if key == "IMPORTED":
            # this duplicates info we already see in import_ok & import_problem
            pass
        elif key == "NODATA":
            self.results.append({'fingerprint': None,
                'problem': '0', 'text': 'No valid data found'})
        elif key == "IMPORT_OK":
            reason, fingerprint = value.split()
            reasons = []
            for code, text in list(self.ok_reason.items()):
                if int(reason) | int(code) == int(reason):
                    reasons.append(text)
            reasontext = '\n'.join(reasons) + "\n"
            self.results.append({'fingerprint': fingerprint,
                'ok': reason, 'text': reasontext})
            self.fingerprints.append(fingerprint)
        elif key == "IMPORT_PROBLEM":
            try:
                reason, fingerprint = value.split()
            except:
                reason = value
                fingerprint = '<unknown>'
            self.results.append({'fingerprint': fingerprint,
                'problem': reason, 'text': self.problem_reason[reason]})
        elif key == "IMPORT_RES":
            import_res = value.split()
            for i in range(len(self.counts)):
                setattr(self, self.counts[i], int(import_res[i]))
        elif key == "KEYEXPIRED":
            self.results.append({'fingerprint': None,
                'problem': '0', 'text': 'Key expired'})
        elif key == "SIGEXPIRED":
            self.results.append({'fingerprint': None,
                'problem': '0', 'text': 'Signature expired'})
        else:
            raise ValueError("Unknown status message: %r" % key)

    def summary(self):
        l = []
        l.append('%d imported'%self.imported)
        if self.not_imported:
            l.append('%d not imported'%self.not_imported)
        return ', '.join(l)

class ListKeys(list):
    ''' Handle status messages for --list-keys.

        Handle pub and uid (relating the latter to the former).

        Don't care about (info from src/DETAILS):

        crt = X.509 certificate
        crs = X.509 certificate and private key available
        sub = subkey (secondary key)
        ssb = secret subkey (secondary key)
        uat = user attribute (same as user id except for field 10).
        sig = signature
        rev = revocation signature
        pkd = public key data (special field format, see below)
        grp = reserved for gpgsm
        rvk = revocation key
    '''
    def __init__(self, gpg):
        self.gpg = gpg
        self.curkey = None
        self.fingerprints = []
        self.uids = []

    def key(self, args):
        vars = ("""
            type trust length algo keyid date expires dummy ownertrust uid
        """).split()
        self.curkey = {}
        for i in range(len(vars)):
            self.curkey[vars[i]] = args[i]
        self.curkey['uids'] = []
        if self.curkey['uid']:
            self.curkey['uids'].append(self.curkey['uid'])
        del self.curkey['uid']
        self.append(self.curkey)

    pub = sec = key

    def fpr(self, args):
        self.curkey['fingerprint'] = args[9]
        self.fingerprints.append(args[9])

    def uid(self, args):
        self.curkey['uids'].append(args[9])
        self.uids.append(args[9])

    def handle_status(self, key, value):
        pass

class Crypt(Verify):
    "Handle status messages for --encrypt and --decrypt"
    def __init__(self, gpg):
        Verify.__init__(self, gpg)
        self.data = ''
        self.ok = False
        self.status = ''

    def __nonzero__(self):
        if self.ok: return True
        return False

    __bool__ = __nonzero__

    def __str__(self):
        return self.data.decode(self.gpg.encoding, self.gpg.decode_errors)

    def handle_status(self, key, value):
        if key in ("ENC_TO", "USERID_HINT", "GOODMDC", "END_DECRYPTION",
                   "BEGIN_SIGNING", "NO_SECKEY", "ERROR", "NODATA",
                   "CARDCTRL"):
            # in the case of ERROR, this is because a more specific error
            # message will have come first
            pass
        elif key in ("NEED_PASSPHRASE", "BAD_PASSPHRASE", "GOOD_PASSPHRASE",
                     "MISSING_PASSPHRASE", "DECRYPTION_FAILED",
                     "KEY_NOT_CREATED"):
            self.status = key.replace("_", " ").lower()
        elif key == "NEED_PASSPHRASE_SYM":
            self.status = 'need symmetric passphrase'
        elif key == "BEGIN_DECRYPTION":
            self.status = 'decryption incomplete'
        elif key == "BEGIN_ENCRYPTION":
            self.status = 'encryption incomplete'
        elif key == "DECRYPTION_OKAY":
            self.status = 'decryption ok'
            self.ok = True
        elif key == "END_ENCRYPTION":
            self.status = 'encryption ok'
            self.ok = True
        elif key == "INV_RECP":
            self.status = 'invalid recipient'
        elif key == "KEYEXPIRED":
            self.status = 'key expired'
        elif key == "SIG_CREATED":
            self.status = 'sig created'
        elif key == "SIGEXPIRED":
            self.status = 'sig expired'
        else:
            Verify.handle_status(self, key, value)

class GenKey(object):
    "Handle status messages for --gen-key"
    def __init__(self, gpg):
        self.gpg = gpg
        self.type = None
        self.fingerprint = None

    def __nonzero__(self):
        if self.fingerprint: return True
        return False

    __bool__ = __nonzero__

    def __str__(self):
        return self.fingerprint or ''

    def handle_status(self, key, value):
        if key in ("PROGRESS", "GOOD_PASSPHRASE", "NODATA"):
            pass
        elif key == "KEY_CREATED":
            (self.type,self.fingerprint) = value.split()
        else:
            raise ValueError("Unknown status message: %r" % key)

class DeleteResult(object):
    "Handle status messages for --delete-key and --delete-secret-key"
    def __init__(self, gpg):
        self.gpg = gpg
        self.status = 'ok'

    def __str__(self):
        return self.status

    problem_reason = {
        '1': 'No such key',
        '2': 'Must delete secret key first',
        '3': 'Ambigious specification',
    }

    def handle_status(self, key, value):
        if key == "DELETE_PROBLEM":
            self.status = self.problem_reason.get(value,
                                                  "Unknown error: %r" % value)
        else:
            raise ValueError("Unknown status message: %r" % key)

class Sign(object):
    "Handle status messages for --sign"
    def __init__(self, gpg):
        self.gpg = gpg
        self.type = None
        self.fingerprint = None

    def __nonzero__(self):
        return self.fingerprint is not None

    __bool__ = __nonzero__

    def __str__(self):
        return self.data.decode(self.gpg.encoding, self.gpg.decode_errors)

    def handle_status(self, key, value):
        if key in ("USERID_HINT", "NEED_PASSPHRASE", "BAD_PASSPHRASE",
                   "GOOD_PASSPHRASE", "BEGIN_SIGNING", "CARDCTRL"):
            pass
        elif key == "SIG_CREATED":
            (self.type,
             algo, hashalgo, cls,
             self.timestamp, self.fingerprint
             ) = value.split()
        else:
            raise ValueError("Unknown status message: %r" % key)


class GPG(object):

    decode_errors = 'strict'

    result_map = {
        'crypt': Crypt,
        'delete': DeleteResult,
        'generate': GenKey,
        'import': ImportResult,
        'list': ListKeys,
        'sign': Sign,
        'verify': Verify,
    }

    "Encapsulate access to the gpg executable"
    def __init__(self, gpgbinary='gpg', gnupghome=None, verbose=False,
                 use_agent=False, keyring=None):
        """Initialize a GPG process wrapper.  Options are:

        gpgbinary -- full pathname for GPG binary.

        gnupghome -- full pathname to where we can find the public and
        private keyrings.  Default is whatever gpg defaults to.
        keyring -- name of alternative keyring file to use. If specified,
        the default keyring is not used.
        """
        self.gpgbinary = gpgbinary
        self.gnupghome = gnupghome
        self.keyring = keyring
        self.verbose = verbose
        self.use_agent = use_agent
        self.encoding = locale.getpreferredencoding()
        if self.encoding is None: # This happens on Jython!
            self.encoding = sys.stdin.encoding
        if gnupghome and not os.path.isdir(self.gnupghome):
            os.makedirs(self.gnupghome,0x1C0)
        p = self._open_subprocess(["--version"])
        result = self.result_map['verify'](self) # any result will do for this
        self._collect_output(p, result, stdin=p.stdin)
        if p.returncode != 0:
            raise ValueError("Error invoking gpg: %s: %s" % (p.returncode,
                                                             result.stderr))

    def _open_subprocess(self, args, passphrase=False):
        # Internal method: open a pipe to a GPG subprocess and return
        # the file objects for communicating with it.
        cmd = [self.gpgbinary, '--status-fd 2 --no-tty']
        if self.gnupghome:
            cmd.append('--homedir "%s" ' % self.gnupghome)
        if self.keyring:
            cmd.append('--no-default-keyring --keyring "%s" ' % self.keyring)
        if passphrase:
            cmd.append('--batch --passphrase-fd 0')
        if self.use_agent:
            cmd.append('--use-agent')
        cmd.extend(args)
        cmd = ' '.join(cmd)
        if self.verbose:
            print(cmd)
        logger.debug("%s", cmd)
        return Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    def _read_response(self, stream, result):
        # Internal method: reads all the stderr output from GPG, taking notice
        # only of lines that begin with the magic [GNUPG:] prefix.
        #
        # Calls methods on the response object for each valid token found,
        # with the arg being the remainder of the status line.
        lines = []
        while True:
            line = stream.readline()
            if len(line) == 0:
                break
            lines.append(line)
            line = line.rstrip()
            if self.verbose:
                print(line)
            logger.debug("%s", line)
            if line[0:9] == '[GNUPG:] ':
                # Chop off the prefix
                line = line[9:]
                L = line.split(None, 1)
                keyword = L[0]
                if len(L) > 1:
                    value = L[1]
                else:
                    value = ""
                result.handle_status(keyword, value)
        result.stderr = ''.join(lines)

    def _read_data(self, stream, result):
        # Read the contents of the file from GPG's stdout
        chunks = []
        while True:
            data = stream.read(1024)
            if len(data) == 0:
                break
            logger.debug("chunk: %r" % data[:256])
            chunks.append(data)
        if _py3k:
            # Join using b'' or '', as appropriate
            result.data = type(data)().join(chunks)
        else:
            result.data = ''.join(chunks)

    def _collect_output(self, process, result, writer=None, stdin=None):
        """
        Drain the subprocesses output streams, writing the collected output
        to the result. If a writer thread (writing to the subprocess) is given,
        make sure it's joined before returning. If a stdin stream is given,
        close it before returning.
        """
        stderr = codecs.getreader(self.encoding)(process.stderr)
        rr = threading.Thread(target=self._read_response, args=(stderr, result))
        rr.setDaemon(True)
        logger.debug('stderr reader: %r', rr)
        rr.start()

        stdout = process.stdout
        dr = threading.Thread(target=self._read_data, args=(stdout, result))
        dr.setDaemon(True)
        logger.debug('stdout reader: %r', dr)
        dr.start()

        dr.join()
        rr.join()
        if writer is not None:
            writer.join()
        process.wait()
        if stdin is not None:
            try:
                stdin.close()
            except IOError:
                pass
        stderr.close()
        stdout.close()

    def _handle_io(self, args, file, result, passphrase=None, binary=False):
        "Handle a call to GPG - pass input data, collect output data"
        # Handle a basic data call - pass data to GPG, handle the output
        # including status information. Garbage In, Garbage Out :)
        p = self._open_subprocess(args, passphrase is not None)
        if not binary:
            stdin = codecs.getwriter(self.encoding)(p.stdin)
        else:
            stdin = p.stdin
        if passphrase:
            _write_passphrase(stdin, passphrase, self.encoding)
        writer = _threaded_copy_data(file, stdin)
        self._collect_output(p, result, writer, stdin)
        return result

    #
    # SIGNATURE METHODS
    #
    def sign(self, message, **kwargs):
        """sign message"""
        f = _make_binary_stream(message, self.encoding)
        result = self.sign_file(f, **kwargs)
        f.close()
        return result

    def sign_file(self, file, keyid=None, passphrase=None, clearsign=True,
                  detach=False, binary=False):
        """sign file"""
        logger.debug("sign_file: %s", file)
        if binary:
            args = ['-s']
        else:
            args = ['-sa']
        # You can't specify detach-sign and clearsign together: gpg ignores
        # the detach-sign in that case.
        if detach:
            args.append("--detach-sign")
        elif clearsign:
            args.append("--clearsign")
        if keyid:
            args.append('--default-key "%s"' % keyid)
        args.extend(['--no-version', "--comment ''"])
        result = self.result_map['sign'](self)
        #We could use _handle_io here except for the fact that if the
        #passphrase is bad, gpg bails and you can't write the message.
        p = self._open_subprocess(args, passphrase is not None)
        try:
            stdin = p.stdin
            if passphrase:
                _write_passphrase(stdin, passphrase, self.encoding)
            writer = _threaded_copy_data(file, stdin)
        except IOError:
            logging.exception("error writing message")
            writer = None
        self._collect_output(p, result, writer, stdin)
        return result

    def verify(self, data):
        """Verify the signature on the contents of the string 'data'

        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input(Passphrase='foo')
        >>> key = gpg.gen_key(input)
        >>> assert key
        >>> sig = gpg.sign('hello',keyid=key.fingerprint,passphrase='bar')
        >>> assert not sig
        >>> sig = gpg.sign('hello',keyid=key.fingerprint,passphrase='foo')
        >>> assert sig
        >>> verify = gpg.verify(sig.data)
        >>> assert verify

        """
        f = _make_binary_stream(data, self.encoding)
        result = self.verify_file(f)
        f.close()
        return result

    def verify_file(self, file, data_filename=None):
        "Verify the signature on the contents of the file-like object 'file'"
        logger.debug('verify_file: %r, %r', file, data_filename)
        result = self.result_map['verify'](self)
        args = ['--verify']
        if data_filename is None:
            self._handle_io(args, file, result, binary=True)
        else:
            logger.debug('Handling detached verification')
            import tempfile
            fd, fn = tempfile.mkstemp(prefix='pygpg')
            s = file.read()
            file.close()
            logger.debug('Wrote to temp file: %r', s)
            os.write(fd, s)
            os.close(fd)
            args.append(fn)
            args.append('"%s"' % data_filename)
            try:
                p = self._open_subprocess(args)
                self._collect_output(p, result, stdin=p.stdin)
            finally:
                os.unlink(fn)
        return result

    #
    # KEY MANAGEMENT
    #

    def import_keys(self, key_data):
        """ import the key_data into our keyring

        >>> import shutil
        >>> shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> pubkey1 = gpg.export_keys(print1)
        >>> seckey1 = gpg.export_keys(print1,secret=True)
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> str(gpg.delete_keys(print1))
        'Must delete secret key first'
        >>> str(gpg.delete_keys(print1,secret=True))
        'ok'
        >>> str(gpg.delete_keys(print1))
        'ok'
        >>> str(gpg.delete_keys("nosuchkey"))
        'No such key'
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert not print1 in seckeys.fingerprints
        >>> assert not print1 in pubkeys.fingerprints
        >>> result = gpg.import_keys('foo')
        >>> assert not result
        >>> result = gpg.import_keys(pubkey1)
        >>> pubkeys = gpg.list_keys()
        >>> seckeys = gpg.list_keys(secret=True)
        >>> assert not print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> result = gpg.import_keys(seckey1)
        >>> assert result
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> assert print2 in pubkeys.fingerprints

        """
        result = self.result_map['import'](self)
        logger.debug('import_keys: %r', key_data[:256])
        data = _make_binary_stream(key_data, self.encoding)
        self._handle_io(['--import'], data, result, binary=True)
        logger.debug('import_keys result: %r', result.__dict__)
        data.close()
        return result

    def recv_keys(self, keyserver, *keyids):
        """Import a key from a keyserver

        >>> import shutil
        >>> shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> result = gpg.recv_keys('pgp.mit.edu', '3FF0DB166A7476EA')
        >>> assert result

        """
        result = self.result_map['import'](self)
        logger.debug('recv_keys: %r', keyids)
        data = _make_binary_stream("", self.encoding)
        #data = ""
        args = ['--keyserver', keyserver, '--recv-keys']
        args.extend(keyids)
        self._handle_io(args, data, result, binary=True)
        logger.debug('recv_keys result: %r', result.__dict__)
        data.close()
        return result

    def delete_keys(self, fingerprints, secret=False):
        which='key'
        if secret:
            which='secret-key'
        if _is_sequence(fingerprints):
            fingerprints = ' '.join(fingerprints)
        args = ['--batch --delete-%s "%s"' % (which, fingerprints)]
        result = self.result_map['delete'](self)
        p = self._open_subprocess(args)
        self._collect_output(p, result, stdin=p.stdin)
        return result

    def export_keys(self, keyids, secret=False):
        "export the indicated keys. 'keyid' is anything gpg accepts"
        which=''
        if secret:
            which='-secret-key'
        if _is_sequence(keyids):
            keyids = ' '.join(['"%s"' % k for k in keyids])
        args = ["--armor --export%s %s" % (which, keyids)]
        p = self._open_subprocess(args)
        # gpg --export produces no status-fd output; stdout will be
        # empty in case of failure
        #stdout, stderr = p.communicate()
        result = self.result_map['delete'](self) # any result will do
        self._collect_output(p, result, stdin=p.stdin)
        logger.debug('export_keys result: %r', result.data)
        return result.data.decode(self.encoding, self.decode_errors)

    def list_keys(self, secret=False):
        """ list the keys currently in the keyring

        >>> import shutil
        >>> shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in pubkeys.fingerprints
        >>> assert print2 in pubkeys.fingerprints

        """

        which='keys'
        if secret:
            which='secret-keys'
        args = "--list-%s --fixed-list-mode --fingerprint --with-colons" % (which,)
        args = [args]
        p = self._open_subprocess(args)

        # there might be some status thingumy here I should handle... (amk)
        # ...nope, unless you care about expired sigs or keys (stevegt)

        # Get the response information
        result = self.result_map['list'](self)
        self._collect_output(p, result, stdin=p.stdin)
        lines = result.data.decode(self.encoding,
                                   self.decode_errors).splitlines()
        valid_keywords = 'pub uid sec fpr'.split()
        for line in lines:
            if self.verbose:
                print(line)
            logger.debug("line: %r", line.rstrip())
            if not line:
                break
            L = line.strip().split(':')
            if not L:
                continue
            keyword = L[0]
            if keyword in valid_keywords:
                getattr(result, keyword)(L)
        return result

    def gen_key(self, input):
        """Generate a key; you might use gen_key_input() to create the
        control input.

        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> assert result
        >>> result = gpg.gen_key('foo')
        >>> assert not result

        """
        args = ["--gen-key --batch"]
        result = self.result_map['generate'](self)
        f = _make_binary_stream(input, self.encoding)
        self._handle_io(args, f, result, binary=True)
        f.close()
        return result

    def gen_key_input(self, **kwargs):
        """
        Generate --gen-key input per gpg doc/DETAILS
        """
        parms = {}
        for key, val in list(kwargs.items()):
            key = key.replace('_','-').title()
            parms[key] = val
        parms.setdefault('Key-Type','RSA')
        parms.setdefault('Key-Length',1024)
        parms.setdefault('Name-Real', "Autogenerated Key")
        parms.setdefault('Name-Comment', "Generated by gnupg.py")
        try:
            logname = os.environ['LOGNAME']
        except KeyError:
            logname = os.environ['USERNAME']
        hostname = socket.gethostname()
        parms.setdefault('Name-Email', "%s@%s" % (logname.replace(' ', '_'),
                                                  hostname))
        out = "Key-Type: %s\n" % parms.pop('Key-Type')
        for key, val in list(parms.items()):
            out += "%s: %s\n" % (key, val)
        out += "%commit\n"
        return out

        # Key-Type: RSA
        # Key-Length: 1024
        # Name-Real: ISdlink Server on %s
        # Name-Comment: Created by %s
        # Name-Email: isdlink@%s
        # Expire-Date: 0
        # %commit
        #
        #
        # Key-Type: DSA
        # Key-Length: 1024
        # Subkey-Type: ELG-E
        # Subkey-Length: 1024
        # Name-Real: Joe Tester
        # Name-Comment: with stupid passphrase
        # Name-Email: joe@foo.bar
        # Expire-Date: 0
        # Passphrase: abc
        # %pubring foo.pub
        # %secring foo.sec
        # %commit

    #
    # ENCRYPTION
    #
    def encrypt_file(self, file, recipients, sign=None,
            always_trust=False, passphrase=None,
            armor=True, output=None, symmetric=False):
        "Encrypt the message read from the file-like object 'file'"
        args = ['--no-version', "--comment ''"]
        if symmetric:
            args.append('--symmetric')
        else:
            args.append('--encrypt')
            if not _is_sequence(recipients):
                recipients = (recipients,)
            for recipient in recipients:
                args.append('--recipient "%s"' % recipient)
        if armor:   # create ascii-armored output - set to False for binary output
            args.append('--armor')
        if output:  # write the output to a file with the specified name
            if os.path.exists(output):
                os.remove(output) # to avoid overwrite confirmation message
            args.append('--output "%s"' % output)
        if sign:
            args.append('--sign --default-key "%s"' % sign)
        if always_trust:
            args.append("--always-trust")
        result = self.result_map['crypt'](self)
        self._handle_io(args, file, result, passphrase=passphrase, binary=True)
        logger.debug('encrypt result: %r', result.data)
        return result

    def encrypt(self, data, recipients, **kwargs):
        """Encrypt the message contained in the string 'data'

        >>> import shutil
        >>> if os.path.exists("keys"):
        ...     shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input(passphrase='foo')
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> result = gpg.encrypt("hello",print2)
        >>> message = str(result)
        >>> assert message != 'hello'
        >>> result = gpg.decrypt(message)
        >>> assert result
        >>> str(result)
        'hello'
        >>> result = gpg.encrypt("hello again",print1)
        >>> message = str(result)
        >>> result = gpg.decrypt(message)
        >>> result.status == 'need passphrase'
        True
        >>> result = gpg.decrypt(message,passphrase='bar')
        >>> result.status in ('decryption failed', 'bad passphrase')
        True
        >>> assert not result
        >>> result = gpg.decrypt(message,passphrase='foo')
        >>> result.status == 'decryption ok'
        True
        >>> str(result)
        'hello again'
        >>> result = gpg.encrypt("signed hello",print2,sign=print1)
        >>> result.status == 'need passphrase'
        True
        >>> result = gpg.encrypt("signed hello",print2,sign=print1,passphrase='foo')
        >>> result.status == 'encryption ok'
        True
        >>> message = str(result)
        >>> result = gpg.decrypt(message)
        >>> result.status == 'decryption ok'
        True
        >>> assert result.fingerprint == print1

        """
        data = _make_binary_stream(data, self.encoding)
        result = self.encrypt_file(data, recipients, **kwargs)
        data.close()
        return result

    def decrypt(self, message, **kwargs):
        data = _make_binary_stream(message, self.encoding)
        result = self.decrypt_file(data, **kwargs)
        data.close()
        return result

    def decrypt_file(self, file, always_trust=False, passphrase=None,
                     output=None):
        args = ["--decrypt"]
        if output:  # write the output to a file with the specified name
            if os.path.exists(output):
                os.remove(output) # to avoid overwrite confirmation message
            args.append('--output "%s"' % output)
        if always_trust:
            args.append("--always-trust")
        result = self.result_map['crypt'](self)
        self._handle_io(args, file, result, passphrase, binary=True)
        logger.debug('decrypt result: %r', result.data)
        return result

