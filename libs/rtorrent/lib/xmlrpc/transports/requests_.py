import requests
import requests.auth
import xmlrpclib


class RequestsTransport(xmlrpclib.Transport):
    def __init__(self, secure, auth=None, proxies=None, verify_ssl=True):
        xmlrpclib.Transport.__init__(self)

        self.secure = secure

        # Construct session
        self.session = requests.Session()
        self.session.auth = self.parse_auth(auth)
        self.session.proxies = proxies or {}
        self.session.verify = verify_ssl

    @property
    def scheme(self):
        if self.secure:
            return 'https'

        return 'http'

    def build_url(self, host, handler):
        return '%s://%s' % (self.scheme, host + handler)

    def request(self, host, handler, request_body, verbose=0):
        # Retry request once if cached connection has gone cold
        for i in (0, 1):
            try:
                return self.single_request(host, handler, request_body, verbose)
            except requests.ConnectionError:
                if i:
                    raise
            except requests.Timeout:
                if i:
                    raise

    def single_request(self, host, handler, request_body, verbose=0):
        url = self.build_url(host, handler)

        # Send request
        response = self.session.post(
            url,
            data=request_body,
            headers={
                'Content-Type': 'text/xml'
            },
            stream=True
        )

        if response.status_code == 200:
            return self.parse_response(response)

        # Invalid response returned
        raise xmlrpclib.ProtocolError(
            host + handler,
            response.status_code, response.reason,
            response.headers
        )

    def parse_auth(self, auth):
        # Parse "auth" parameter
        if type(auth) is not tuple or len(auth) != 3:
            return None

        method, username, password = auth

        # Basic Authentication
        if method == 'basic':
            return requests.auth.HTTPBasicAuth(username, password)

        # Digest Authentication
        if method == 'digest':
            return requests.auth.HTTPDigestAuth(username, password)

        raise NotImplementedError('Unsupported authentication method: %r' % method)

    def parse_response(self, response):
        p, u = self.getparser()

        # Write chunks to parser
        for chunk in response.iter_content(1024):
            p.feed(chunk)

        # Close parser
        p.close()

        # Close unmarshaller
        return u.close()
