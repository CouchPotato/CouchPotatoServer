# -*- coding: utf-8 -*-
# Changed 
# Removed iso8601 library requirement 
# Added CP logging

import os
import json
import binascii
import webbrowser
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from datetime import datetime

import tus
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from couchpotato import CPLog


KB = 1024
MB = 1024 * KB

# Read and write operations are limited to this chunk size.
# This can make a big difference when dealing with large files.
CHUNK_SIZE = 256 * KB

BASE_URL = 'https://api.put.io/v2'
UPLOAD_URL = 'https://upload.put.io/v2/files/upload'
TUS_UPLOAD_URL = 'https://upload.put.io/files/'
ACCESS_TOKEN_URL = 'https://api.put.io/v2/oauth2/access_token'
AUTHENTICATION_URL = 'https://api.put.io/v2/oauth2/authenticate'

log = CPLog(__name__)


class APIError(Exception):
    pass


class ClientError(APIError):
    pass


class ServerError(APIError):
    pass


class AuthHelper(object):

    def __init__(self, client_id, client_secret, redirect_uri, type='code'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = redirect_uri
        self.type = type

    @property
    def authentication_url(self):
        """Redirect your users to here to authenticate them."""
        params = {
            'client_id': self.client_id,
            'response_type': self.type,
            'redirect_uri': self.callback_url
        }
        return AUTHENTICATION_URL + "?" + urlencode(params)

    def open_authentication_url(self):
        webbrowser.open(self.authentication_url)

    def get_access_token(self, code):
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': self.callback_url,
            'code': code
        }
        response = requests.get(ACCESS_TOKEN_URL, params=params)
        log.debug(response)
        assert response.status_code == 200
        return response.json()['access_token']


class Client(object):

    def __init__(self, access_token, use_retry=False):
        self.access_token = access_token
        self.session = requests.session()

        if use_retry:
            # Retry maximum 10 times, backoff on each retry
            # Sleeps 1s, 2s, 4s, 8s, etc to a maximum of 120s between retries
            # Retries on HTTP status codes 500, 502, 503, 504
            retries = Retry(total=10,
                            backoff_factor=1,
                            status_forcelist=[500, 502, 503, 504])

            # Use the retry strategy for all HTTPS requests
            self.session.mount('https://', HTTPAdapter(max_retries=retries))

        # Keep resource classes as attributes of client.
        # Pass client to resource classes so resource object
        # can use the client.
        attributes = {'client': self}
        self.File = type('File', (_File,), attributes)
        self.Transfer = type('Transfer', (_Transfer,), attributes)
        self.Account = type('Account', (_Account,), attributes)

    def request(self, path, method='GET', params=None, data=None, files=None,
                headers=None, raw=False, allow_redirects=True, stream=False):
        """
        Wrapper around requests.request()

        Prepends BASE_URL to path.
        Inserts oauth_token to query params.
        Parses response as JSON and returns it.

        """
        if not params:
            params = {}

        if not headers:
            headers = {}

        # All requests must include oauth_token
        params['oauth_token'] = self.access_token

        headers['Accept'] = 'application/json'

        if path.startswith('https://'):
            url = path
        else:
            url = BASE_URL + path
        log.debug('url: %s', url)

        response = self.session.request(
            method, url, params=params, data=data, files=files,
            headers=headers, allow_redirects=allow_redirects, stream=stream)
        log.debug('response: %s', response)
        if raw:
            return response

        log.debug('content: %s', response.content)
        try:
            body = json.loads(response.content.decode())
        except ValueError:
            raise ServerError('InvalidJSON', response.content)

        if body['status'] == 'ERROR':
            log.error("API returned error: %s", body)
            exception_class = {'4': ClientError, '5': ServerError}[str(response.status_code)[0]]
            raise exception_class(body['error_type'], body['error_message'])

        return body


class _BaseResource(object):

    client = None

    def __init__(self, resource_dict):
        """Constructs the object from a dict."""
        # All resources must have id and name attributes
        self.id = None
        self.name = None
        self.__dict__.update(resource_dict)
        try:
            self.created_at = strptime(self.created_at)
        except Exception:
            self.created_at = None

    def __str__(self):
        return self.name.encode('utf-8')

    def __repr__(self):
        # shorten name for display
        name = self.name[:17] + '...' if len(self.name) > 20 else self.name
        return '<%s id=%r, name=%r>' % (
            self.__class__.__name__, self.id, name)


class _File(_BaseResource):

    @classmethod
    def get(cls, id):
        d = cls.client.request('/files/%i' % id, method='GET')
        t = d['file']
        return cls(t)

    @classmethod
    def list(cls, parent_id=0):
        d = cls.client.request('/files/list', params={'parent_id': parent_id})
        files = d['files']
        return [cls(f) for f in files]

    @classmethod
    def upload(cls, path, name=None, parent_id=0):
        with open(path) as f:
            if name:
                files = {'file': (name, f)}
            else:
                files = {'file': f}
            d = cls.client.request(UPLOAD_URL, method='POST',
                                   data={'parent_id': parent_id}, files=files)

        f = d['file']
        return cls(f)

    @classmethod
    def upload_tus(cls, path, name=None, parent_id=0):
        headers = {'Authorization': 'token %s' % cls.client.access_token}
        metadata = {'parent_id': str(parent_id)}
        if name:
            metadata['name'] = name
        with open(path) as f:
            tus.upload(f, TUS_UPLOAD_URL, file_name=name, headers=headers, metadata=metadata)

    def dir(self):
        """List the files under directory."""
        return self.list(parent_id=self.id)

    def download(self, dest='.', delete_after_download=False, chunk_size=CHUNK_SIZE):
        if self.content_type == 'application/x-directory':
            self._download_directory(dest, delete_after_download, chunk_size)
        else:
            self._download_file(dest, delete_after_download, chunk_size)

    def _download_directory(self, dest, delete_after_download, chunk_size):
        name = _str(self.name)

        dest = os.path.join(dest, name)
        if not os.path.exists(dest):
            os.mkdir(dest)

        for sub_file in self.dir():
            sub_file.download(dest, delete_after_download, chunk_size)

        if delete_after_download:
            self.delete()

    def _verify_file(self, filepath):
        log.info('verifying crc32...')
        filesize = os.path.getsize(filepath)
        if self.size != filesize:
            logging.error('file %s is %d bytes, should be %s bytes' % (filepath, filesize, self.size))
            return False

        crcbin = 0
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                crcbin = binascii.crc32(chunk, crcbin) & 0xffffffff

        crc32 = '%08x' % crcbin

        if crc32 != self.crc32:
            logging.error('file %s CRC32 is %s, should be %s' % (filepath, crc32, self.crc32))
            return False

        return True

    def _download_file(self, dest, delete_after_download, chunk_size):
        name = _str(self.name)

        filepath = os.path.join(dest, name)
        if os.path.exists(filepath):
            first_byte = os.path.getsize(filepath)

            if first_byte == self.size:
                log.warning('file %s exists and is the correct size %d' % (filepath, self.size))
        else:
            first_byte = 0

        log.debug('file %s is currently %d, should be %d' % (filepath, first_byte, self.size))

        if self.size == 0:
            # Create an empty file
            open(filepath, 'w').close()
            log.debug('created empty file %s' % filepath)
        else:
            if first_byte < self.size:
                with open(filepath, 'ab') as f:
                    headers = {'Range': 'bytes=%d-' % first_byte}

                    log.debug('request range: bytes=%d-' % first_byte)
                    response = self.client.request('/files/%s/download' % self.id,
                                                   headers=headers,
                                                   raw=True,
                                                   stream=True)

                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)

        if self._verify_file(filepath):
            if delete_after_download:
                self.delete()

    def delete(self):
        return self.client.request('/files/delete', method='POST',
                                   data={'file_id': str(self.id)})

    @classmethod
    def delete_multi(cls, ids):
        return cls.client.request('/files/delete', method='POST',
                                  data={'file_ids': ','.join(map(str, ids))})

    def move(self, parent_id):
        return self.client.request('/files/move', method='POST',
                                   data={'file_ids': str(self.id), 'parent_id': str(parent_id)})

    def rename(self, name):
        return self.client.request('/files/rename', method='POST',
                                   data={'file_id': str(self.id), 'name': str(name)})


class _Transfer(_BaseResource):

    @classmethod
    def list(cls):
        d = cls.client.request('/transfers/list')
        transfers = d['transfers']
        return [cls(t) for t in transfers]

    @classmethod
    def get(cls, id):
        d = cls.client.request('/transfers/%i' % id, method='GET')
        t = d['transfer']
        return cls(t)

    @classmethod
    def add_url(cls, url, parent_id=0, extract=False, callback_url=None):
        log.debug('callback_url is %s', callback_url) 
        d = cls.client.request('/transfers/add', method='POST', data=dict(
            url=url, save_parent_id=parent_id, extract=extract,
            callback_url=callback_url))
        t = d['transfer']
        return cls(t)

    @classmethod
    def add_torrent(cls, path, parent_id=0, extract=False, callback_url=None):
        with open(path, 'rb') as f:
            files = {'file': f}
            d = cls.client.request('/files/upload', method='POST', files=files,
                                   data=dict(parent_id=parent_id,
                                             extract=extract,
                                             callback_url=callback_url))
        t = d['transfer']
        return cls(t)

    @classmethod
    def clean(cls):
        return cls.client.request('/transfers/clean', method='POST')

    def cancel(self):
        return self.client.request('/transfers/cancel',
                                   method='POST',
                                   data={'transfer_ids': self.id})

    @classmethod
    def cancel_multi(cls, ids):
        return cls.client.request('/transfers/cancel',
                                  method='POST',
                                  data={'transfer_ids': ','.join(map(str, ids))})


class _Account(_BaseResource):

    @classmethod
    def info(cls):
        return cls.client.request('/account/info', method='GET')

    @classmethod
    def settings(cls):
        return cls.client.request('/account/settings', method='GET')


# Due to a nasty bug in datetime module, datetime.strptime calls
# are not thread-safe and can throw a TypeError. Details: https://bugs.python.org/issue7980
# Here we are implementing simple RFC3339 parser which is used in Put.io APIv2.
def strptime(date):
    """Returns datetime object from the given date, which is in a specific format: YYYY-MM-ddTHH:mm:ss"""
    d = {
        'year': date[0:4],
        'month': date[5:7],
        'day': date[8:10],
        'hour': date[11:13],
        'minute': date[14:16],
        'second': date[17:],
    }

    d = dict((k, int(v)) for k, v in d.iteritems())
    return datetime(**d)


def _str(s):
    """Python 3 compatibility function for converting to str."""
    try:
        if isinstance(s, unicode):
            return s.encode('utf-8', 'replace')
    except NameError:
        pass
    return s
