import requests
import json

class LoginRequired(Exception):
    def __str__(self):
        return 'Please login first.'


class QBittorrentClient(object):
    """class to interact with qBittorrent WEB API"""
    def __init__(self, url):
        if not url.endswith('/'):
            url += '/'
        self.url = url

        session = requests.Session()
        check_prefs = session.get(url+'api/v2/app/preferences')

        if check_prefs.status_code == 200:
            self._is_authenticated = True
            self.session = session
        else:
            self._is_authenticated = False

    def _get(self, endpoint, **kwargs):
        """
        Method to perform GET request on the API.

        :param endpoint: Endpoint of the API.
        :param kwargs: Other keyword arguments for requests.

        :return: Response of the GET request.
        """
        return self._request(endpoint, 'get', **kwargs)

    def _post(self, endpoint, data, **kwargs):
        """
        Method to perform POST request on the API.

        :param endpoint: Endpoint of the API.
        :param data: POST DATA for the request.
        :param kwargs: Other keyword arguments for requests.

        :return: Response of the POST request.
        """
        return self._request(endpoint, 'post', data, **kwargs)

    def _request(self, endpoint, method, data=None, **kwargs):
        """
        Method to hanle both GET and POST requests.

        :param endpoint: Endpoint of the API.
        :param method: Method of HTTP request.
        :param data: POST DATA for the request.
        :param kwargs: Other keyword arguments.

        :return: Response for the request.
        """
        final_url = self.url + endpoint

        if not self._is_authenticated:
            raise LoginRequired

        rq = self.session
        if method == 'get':
            request = rq.get(final_url, **kwargs)
        else:
            request = rq.post(final_url, data, **kwargs)

        request.raise_for_status()

        if len(request.text) == 0:
            data = json.loads('{}')
        else:
            try:
                data = json.loads(request.text)
            except ValueError:
                data = request.text

        return data

    def login(self, username, password):
        """
        Method to authenticate the qBittorrent Client.

        Declares a class attribute named ``session`` which
        stores the authenticated session if the login is correct.
        Else, shows the login error.

        :param username: Username.
        :param password: Password.

        :return: Response to login request to the API.
        """
        self.session = requests.Session()
        login = self.session.post(self.url+'api/v2/auth/login',
                                  data={'username': username,
                                        'password': password})
        if login.text == 'Ok.':
            self._is_authenticated = True
        else:
            return login.text

    def logout(self):
        """
        Logout the current session.
        """
        response = self._get('api/v2/auth/logout')
        self._is_authenticated = False
        return response

    @property
    def qbittorrent_version(self):
        """
        Get qBittorrent version.
        """
        return self._get('api/v2/app/version')

    @property
    def api_version(self):
        """
        Get WEB API version.
        """
        return self._get('api/v2/app/webapiVersion')

    @property
    def api_min_version(self):
        """
        Get minimum WEB API version.
        """
        return self._get('api/v2/app/webapiVersion')

    def shutdown(self):
        """
        Shutdown qBittorrent.
        """
        return self._get('command/shutdown')

    def torrents(self, status='active', label='', sort='priority',
                 reverse=False, limit=10, offset=0):
        """
        Returns a list of torrents matching the supplied filters.

        :param status: Current status of the torrents.
        :param label: Fetch all torrents with the supplied label. qbittorrent < 3.3.5
        :param category: Fetch all torrents with the supplied label. qbittorrent >= 3.3.5
        :param sort: Sort torrents by.
        :param reverse: Enable reverse sorting.
        :param limit: Limit the number of torrents returned.
        :param offset: Set offset (if less than 0, offset from end).

        :return: list() of torrent with matching filter.
        """

        STATUS_LIST = ['all', 'downloading', 'completed',
                       'paused', 'active', 'inactive']
        if status not in STATUS_LIST:
            raise ValueError("Invalid status.")
        
        if self.api_version < 10:
            params = {
                'filter': status,
                'label': label,
                'sort': sort,
                'reverse': reverse,
                'limit': limit,
                'offset': offset
            }
            
        elif self.api_version >= 10:
            params = {
                'filter': status,
                'category': label,
                'sort': sort,
                'reverse': reverse,
                'limit': limit,
                'offset': offset
            }
        
        return self._get('api/v2/torrents/info', params=params)

    def get_torrent(self, infohash):
        """
        Get details of the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._get('api/v2/torrents/properties', params = { 'hash': infohash.lower() })

    def get_torrent_trackers(self, infohash):
        """
        Get trackers for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._get('api/v2/torrents/trackers', params = { 'hash': infohash.lower() })

    def get_torrent_webseeds(self, infohash):
        """
        Get webseeds for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._get('api/v2/torrents/webseeds', params = { 'hash': infohash.lower() })

    def get_torrent_files(self, infohash):
        """
        Get list of files for the torrent.

        :param infohash: INFO HASH of the torrent.
        """
        return self._get('api/v2/torrents/files' + infohash.lower())

    @property
    def global_transfer_info(self):
        """
        Get JSON data of the global transfer info of qBittorrent.
        """
        return self._get('api/v2/transfer/info')

    @property
    def preferences(self):
        """
        Get the current qBittorrent preferences.
        Can also be used to assign individual preferences.
        For setting multiple preferences at once,
        see ``set_preferences`` method.

        Note: Even if this is a ``property``,
        to fetch the current preferences dict, you are required
        to call it like a bound method.

        Wrong::

            qb.preferences

        Right::

            qb.preferences()

        """
        prefs = self._get('api/v2/app/preferences')

        class Proxy(Client):
            """
            Proxy class to to allow assignment of individual preferences.
            this class overrides some methods to ease things.

            Because of this, settings can be assigned like::

                In [5]: prefs = qb.preferences()

                In [6]: prefs['autorun_enabled']
                Out[6]: True

                In [7]: prefs['autorun_enabled'] = False

                In [8]: prefs['autorun_enabled']
                Out[8]: False

            """

            def __init__(self, url, prefs, auth, session):
                super(Proxy, self).__init__(url)
                self.prefs = prefs
                self._is_authenticated = auth
                self.session = session

            def __getitem__(self, key):
                return self.prefs[key]

            def __setitem__(self, key, value):
                kwargs = {key: value}
                return self.set_preferences(**kwargs)

            def __call__(self):
                return self.prefs

        return Proxy(self.url, prefs, self._is_authenticated, self.session)

    def sync(self, rid=0):
        """
        Sync the torrents by supplied LAST RESPONSE ID.
        Read more @ http://git.io/vEgXr

        :param rid: Response ID of last request.
        """
        return self._get('sync/maindata', params={'rid': rid})

    def download_from_link(self, link,
                           save_path=None, label=''):
        """
        Download torrent using a link.

        :param link: URL Link or list of.
        :param save_path: Path to download the torrent.
        :param label: Label of the torrent(s). qbittorrent < 3.3.5
        :param category: Label of the torrent(s). qbittorrent >= 3.3.5

        :return: Empty JSON data.
        """
        if not isinstance(link, list):
            link = [link]
        data = {'urls': link}

        if save_path:
            data.update({'savepath': save_path})
        if self.api_version < 10 and label:
            data.update({'label': label})
            
        elif self.api_version >= 10 and label:
            data.update({'category': label})
        

        return self._post('api/v2/torrents/add', data=data)

    def download_from_file(self, file_buffer,
                           save_path=None, label=''):
        """
        Download torrent using a file.

        :param file_buffer: Single file() buffer or list of.
        :param save_path: Path to download the torrent.
        :param label: Label of the torrent(s). qbittorrent < 3.3.5
        :param category: Label of the torrent(s). qbittorrent >= 3.3.5

        :return: Empty JSON data.
        """
        if isinstance(file_buffer, list):
            torrent_files = {}
            for i, f in enumerate(file_buffer):
                torrent_files.update({'torrents%s' % i: f})
            print torrent_files
        else:
            torrent_files = {'torrents': file_buffer}

        data = {}

        if save_path:
            data.update({'savepath': save_path})
        if self.api_version < 10 and label:
            data.update({'label': label})
            
        elif self.api_version >= 10 and label:
            data.update({'category': label})
            
        return self._post('api/v2/torrents/add', data=data, files=torrent_files)

    def add_trackers(self, infohash, trackers):
        """
        Add trackers to a torrent.

        :param infohash: INFO HASH of torrent.
        :param trackers: Trackers.
        """
        data = {'hash': infohash.lower(),
                'urls': trackers}
        return self._post('api/v2/torrents/add_trackers', data=data)

    @staticmethod
    def process_infohash_list(infohash_list):
        """
        Method to convert the infohash_list to qBittorrent API friendly values.

        :param infohash_list: List of infohash.
        """
        if isinstance(infohash_list, list):
            data = {'hashes': '|'.join([h.lower() for h in infohash_list])}
        else:
            data = {'hashes': infohash_list.lower()}
        return data

    def pause(self, infohash):
        """
        Pause a torrent.

        :param infohash: INFO HASH of torrent.
        """
        return self._post('api/v2/torrents/pause', data={'hash': infohash.lower()})

    def pause_all(self):
        """
        Pause all torrents.
        """
        return self._get('api/v2/torrents/pause', data={'hash': 'all'})

    def pause_multiple(self, infohash_list):
        """
        Pause multiple torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/pause', data=data)

    def resume(self, infohash):
        """
        Resume a paused torrent.

        :param infohash: INFO HASH of torrent.
        """
        return self._post('api/v2/torrents/resume', data={'hash': infohash.lower()})

    def resume_all(self):
        """
        Resume all torrents.
        """
        return self._get('api/v2/torrents/resume', data={'hash': 'all'})

    def resume_multiple(self, infohash_list):
        """
        Resume multiple paused torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/resume', data=data)

    def delete(self, infohash_list):
        """
        Delete torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/delete', data=data)

    def delete_permanently(self, infohash_list):
        """
        Permanently delete torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/delete', data=data, params= { 'deleteFiles': True})

    def recheck(self, infohash_list):
        """
        Recheck torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/recheck', data=data)

    def increase_priority(self, infohash_list):
        """
        Increase priority of torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/increase_priority', data=data)

    def decrease_priority(self, infohash_list):
        """
        Decrease priority of torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/decrease_priority', data=data)

    def set_max_priority(self, infohash_list):
        """
        Set torrents to maximum priority level.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/top_priority', data=data)

    def set_min_priority(self, infohash_list):
        """
        Set torrents to minimum priority level.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/bottom_priority', data=data)

    def set_file_priority(self, infohash, file_id, priority):
        """
        Set file of a torrent to a supplied priority level.

        :param infohash: INFO HASH of torrent.
        :param file_id: ID of the file to set priority.
        :param priority: Priority level of the file.
        """
        if priority not in [0, 1, 2, 7]:
            raise ValueError("Invalid priority, refer WEB-UI docs for info.")
        elif not isinstance(file_id, int):
            raise TypeError("File ID must be an int")

        data = {'hash': infohash.lower(),
                'id': file_id,
                'priority': priority}

        return self._post('api/v2/torrents/file_priority', data=data)

    # Get-set global download and upload speed limits.

    def get_global_download_limit(self):
        """
        Get global download speed limit.
        """
        return self._get('api/v2/transfer/download_limit')

    def set_global_download_limit(self, limit):
        """
        Set global download speed limit.

        :param limit: Speed limit in bytes.
        """
        return self._post('api/v2/transfer/set_download_limit', data={'limit': limit})

    global_download_limit = property(get_global_download_limit,
                                     set_global_download_limit)

    def get_global_upload_limit(self):
        """
        Get global upload speed limit.
        """
        return self._get('api/v2/transfer/upload_limit')

    def set_global_upload_limit(self, limit):
        """
        Set global upload speed limit.

        :param limit: Speed limit in bytes.
        """
        return self._post('api/v2/transfer/set_upload_limit', data={'limit': limit})

    global_upload_limit = property(get_global_upload_limit,
                                   set_global_upload_limit)

    # Get-set download and upload speed limits of the torrents.
    def get_torrent_download_limit(self, infohash_list):
        """
        Get download speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/download_limit', data=data)

    def set_torrent_download_limit(self, infohash_list, limit):
        """
        Set download speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        :param limit: Speed limit in bytes.
        """
        data = self.process_infohash_list(infohash_list)
        data.update({'limit': limit})
        return self._post('api/v2/transfer/set_download_limit', data=data)

    def get_torrent_upload_limit(self, infohash_list):
        """
        Get upoload speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/upload_limit', data=data)

    def set_torrent_upload_limit(self, infohash_list, limit):
        """
        Set upload speed limit of the supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        :param limit: Speed limit in bytes.
        """
        data = self.process_infohash_list(infohash_list)
        data.update({'limit': limit})
        return self._post('api/v2/transfer/set_upload_limit', data=data)

    # setting preferences
    def set_preferences(self, **kwargs):
        """
        Set preferences of qBittorrent.
        Read all possible preferences @ http://git.io/vEgDQ

        :param kwargs: set preferences in kwargs form.
        """
        json_data = "json={}".format(json.dumps(kwargs))
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        return self._post('api/v2/app/set_preferences', data=json_data,
                          headers=headers)

    def get_alternative_speed_status(self):
        """
        Get Alternative speed limits. (1/0)
        """
        return self._get('api/v2/transfer/speed_limits_mode')

    alternative_speed_status = property(get_alternative_speed_status)

    def toggle_alternative_speed(self):
        """
        Toggle alternative speed limits.
        """
        return self._get('api/v2/transfer/toggle_speed_limits_mode')

    def toggle_sequential_download(self, infohash_list):
        """
        Toggle sequential download in supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/toggle_sequential_download', data=data)

    def toggle_first_last_piece_priority(self, infohash_list):
        """
        Toggle first/last piece priority of supplied torrents.

        :param infohash_list: Single or list() of infohashes.
        """
        data = self.process_infohash_list(infohash_list)
        return self._post('api/v2/torrents/toggle_first_last_piece_priority', data=data)

    def force_start(self, infohash_list, value=True):
        """
        Force start selected torrents.

        :param infohash_list: Single or list() of infohashes.
        :param value: Force start value (bool)
        """
        data = self.process_infohash_list(infohash_list)
        data.update({'value': json.dumps(value)})
        return self._post('api/v2/torrents/set_force_start', data=data)
