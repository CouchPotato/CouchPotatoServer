# -*- coding: utf-8 -*-
from __future__ import absolute_import

"""
oauthlib.oauth1.rfc5849
~~~~~~~~~~~~~~

This module is an implementation of various logic needed
for signing and checking OAuth 1.0 RFC 5849 requests.
"""

import logging
import urlparse

from oauthlib.common import Request, urlencode
from . import parameters, signature, utils

SIGNATURE_HMAC = u"HMAC-SHA1"
SIGNATURE_RSA = u"RSA-SHA1"
SIGNATURE_PLAINTEXT = u"PLAINTEXT"
SIGNATURE_METHODS = (SIGNATURE_HMAC, SIGNATURE_RSA, SIGNATURE_PLAINTEXT)

SIGNATURE_TYPE_AUTH_HEADER = u'AUTH_HEADER'
SIGNATURE_TYPE_QUERY = u'QUERY'
SIGNATURE_TYPE_BODY = u'BODY'

CONTENT_TYPE_FORM_URLENCODED = u'application/x-www-form-urlencoded'


class Client(object):
    """A client used to sign OAuth 1.0 RFC 5849 requests"""
    def __init__(self, client_key,
            client_secret=None,
            resource_owner_key=None,
            resource_owner_secret=None,
            callback_uri=None,
            signature_method=SIGNATURE_HMAC,
            signature_type=SIGNATURE_TYPE_AUTH_HEADER,
            rsa_key=None, verifier=None):
        self.client_key = client_key
        self.client_secret = client_secret
        self.resource_owner_key = resource_owner_key
        self.resource_owner_secret = resource_owner_secret
        self.signature_method = signature_method
        self.signature_type = signature_type
        self.callback_uri = callback_uri
        self.rsa_key = rsa_key
        self.verifier = verifier

        if self.signature_method == SIGNATURE_RSA and self.rsa_key is None:
            raise ValueError('rsa_key is required when using RSA signature method.')

    def get_oauth_signature(self, request):
        """Get an OAuth signature to be used in signing a request
        """
        if self.signature_method == SIGNATURE_PLAINTEXT:
            # fast-path
            return signature.sign_plaintext(self.client_secret,
                self.resource_owner_secret)

        uri, headers, body = self._render(request)

        collected_params = signature.collect_parameters(
            uri_query=urlparse.urlparse(uri).query,
            body=body,
            headers=headers)
        logging.debug("Collected params: {0}".format(collected_params))

        normalized_params = signature.normalize_parameters(collected_params)
        normalized_uri = signature.normalize_base_string_uri(request.uri)
        logging.debug("Normalized params: {0}".format(normalized_params))
        logging.debug("Normalized URI: {0}".format(normalized_uri))

        base_string = signature.construct_base_string(request.http_method,
            normalized_uri, normalized_params)

        logging.debug("Base signing string: {0}".format(base_string))

        if self.signature_method == SIGNATURE_HMAC:
            sig = signature.sign_hmac_sha1(base_string, self.client_secret,
                self.resource_owner_secret)
        elif self.signature_method == SIGNATURE_RSA:
            sig = signature.sign_rsa_sha1(base_string, self.rsa_key)
        else:
            sig = signature.sign_plaintext(self.client_secret,
                self.resource_owner_secret)

        logging.debug("Signature: {0}".format(sig))
        return sig

    def get_oauth_params(self):
        """Get the basic OAuth parameters to be used in generating a signature.
        """
        params = [
            (u'oauth_nonce', utils.generate_nonce()),
            (u'oauth_timestamp', utils.generate_timestamp()),
            (u'oauth_version', u'1.0'),
            (u'oauth_signature_method', self.signature_method),
            (u'oauth_consumer_key', self.client_key),
        ]
        if self.resource_owner_key:
            params.append((u'oauth_token', self.resource_owner_key))
        if self.callback_uri:
            params.append((u'oauth_callback', self.callback_uri))
        if self.verifier:
            params.append((u'oauth_verifier', self.verifier))

        return params

    def _render(self, request, formencode=False):
        """Render a signed request according to signature type

        Returns a 3-tuple containing the request URI, headers, and body.

        If the formencode argument is True and the body contains parameters, it
        is escaped and returned as a valid formencoded string.
        """
        # TODO what if there are body params on a header-type auth?
        # TODO what if there are query params on a body-type auth?

        uri, headers, body = request.uri, request.headers, request.body

        # TODO: right now these prepare_* methods are very narrow in scope--they
        # only affect their little thing. In some cases (for example, with
        # header auth) it might be advantageous to allow these methods to touch
        # other parts of the request, like the headers—so the prepare_headers
        # method could also set the Content-Type header to x-www-form-urlencoded
        # like the spec requires. This would be a fundamental change though, and
        # I'm not sure how I feel about it.
        if self.signature_type == SIGNATURE_TYPE_AUTH_HEADER:
            headers = parameters.prepare_headers(request.oauth_params, request.headers)
        elif self.signature_type == SIGNATURE_TYPE_BODY and request.decoded_body is not None:
            body = parameters.prepare_form_encoded_body(request.oauth_params, request.decoded_body)
            if formencode:
                body = urlencode(body)
            headers['Content-Type'] = u'application/x-www-form-urlencoded'
        elif self.signature_type == SIGNATURE_TYPE_QUERY:
            uri = parameters.prepare_request_uri_query(request.oauth_params, request.uri)
        else:
            raise ValueError('Unknown signature type specified.')

        return uri, headers, body

    def sign(self, uri, http_method=u'GET', body=None, headers=None):
        """Sign a request

        Signs an HTTP request with the specified parts.

        Returns a 3-tuple of the signed request's URI, headers, and body.
        Note that http_method is not returned as it is unaffected by the OAuth
        signing process.

        The body argument may be a dict, a list of 2-tuples, or a formencoded
        string. The Content-Type header must be 'application/x-www-form-urlencoded'
        if it is present.

        If the body argument is not one of the above, it will be returned
        verbatim as it is unaffected by the OAuth signing process. Attempting to
        sign a request with non-formencoded data using the OAuth body signature
        type is invalid and will raise an exception.

        If the body does contain parameters, it will be returned as a properly-
        formatted formencoded string.

        All string data MUST be unicode. This includes strings inside body
        dicts, for example.
        """
        # normalize request data
        request = Request(uri, http_method, body, headers)

        # sanity check
        content_type = request.headers.get('Content-Type', None)
        multipart = content_type and content_type.startswith('multipart/')
        should_have_params = content_type == CONTENT_TYPE_FORM_URLENCODED
        has_params = request.decoded_body is not None
        # 3.4.1.3.1.  Parameter Sources
        # [Parameters are collected from the HTTP request entity-body, but only
        # if [...]:
        #    *  The entity-body is single-part.
        if multipart and has_params:
            raise ValueError("Headers indicate a multipart body but body contains parameters.")
        #    *  The entity-body follows the encoding requirements of the
        #       "application/x-www-form-urlencoded" content-type as defined by
        #       [W3C.REC-html40-19980424].
        elif should_have_params and not has_params:
            raise ValueError("Headers indicate a formencoded body but body was not decodable.")
        #    *  The HTTP request entity-header includes the "Content-Type"
        #       header field set to "application/x-www-form-urlencoded".
        elif not should_have_params and has_params:
            raise ValueError("Body contains parameters but Content-Type header was not set.")

        # 3.5.2.  Form-Encoded Body
        # Protocol parameters can be transmitted in the HTTP request entity-
        # body, but only if the following REQUIRED conditions are met:
        # o  The entity-body is single-part.
        # o  The entity-body follows the encoding requirements of the
        #    "application/x-www-form-urlencoded" content-type as defined by
        #    [W3C.REC-html40-19980424].
        # o  The HTTP request entity-header includes the "Content-Type" header
        #    field set to "application/x-www-form-urlencoded".
        elif self.signature_type == SIGNATURE_TYPE_BODY and not (
                should_have_params and has_params and not multipart):
            raise ValueError('Body signatures may only be used with form-urlencoded content')

        # generate the basic OAuth parameters
        request.oauth_params = self.get_oauth_params()

        # generate the signature
        request.oauth_params.append((u'oauth_signature', self.get_oauth_signature(request)))

        # render the signed request and return it
        return self._render(request, formencode=True)


class Server(object):
    """A server used to verify OAuth 1.0 RFC 5849 requests"""
    def __init__(self, signature_method=SIGNATURE_HMAC, rsa_key=None):
        self.signature_method = signature_method
        self.rsa_key = rsa_key

    def get_client_secret(self, client_key):
        raise NotImplementedError("Subclasses must implement this function.")

    def get_resource_owner_secret(self, resource_owner_key):
        raise NotImplementedError("Subclasses must implement this function.")

    def get_signature_type_and_params(self, uri_query, headers, body):
        signature_types_with_oauth_params = filter(lambda s: s[1], (
            (SIGNATURE_TYPE_AUTH_HEADER, utils.filter_oauth_params(
                signature.collect_parameters(headers=headers,
                exclude_oauth_signature=False))),
            (SIGNATURE_TYPE_BODY, utils.filter_oauth_params(
                signature.collect_parameters(body=body,
                exclude_oauth_signature=False))),
            (SIGNATURE_TYPE_QUERY, utils.filter_oauth_params(
                signature.collect_parameters(uri_query=uri_query,
                exclude_oauth_signature=False))),
        ))

        if len(signature_types_with_oauth_params) > 1:
            raise ValueError('oauth_ params must come from only 1 signature type but were found in %s' % ', '.join(
                [s[0] for s in signature_types_with_oauth_params]))
        try:
            signature_type, params = signature_types_with_oauth_params[0]
        except IndexError:
            raise ValueError('oauth_ params are missing. Could not determine signature type.')

        return signature_type, dict(params)

    def check_client_key(self, client_key):
        raise NotImplementedError("Subclasses must implement this function.")

    def check_resource_owner_key(self, client_key, resource_owner_key):
        raise NotImplementedError("Subclasses must implement this function.")

    def check_timestamp_and_nonce(self, timestamp, nonce):
        raise NotImplementedError("Subclasses must implement this function.")

    def check_request_signature(self, uri, http_method=u'GET', body='',
            headers=None):
        """Check a request's supplied signature to make sure the request is
        valid.

        Servers should return HTTP status 400 if a ValueError exception
        is raised and HTTP status 401 on return value False.

        Per `section 3.2`_ of the spec.

        .. _`section 3.2`: http://tools.ietf.org/html/rfc5849#section-3.2
        """
        headers = headers or {}
        signature_type = None
        # FIXME: urlparse does not return unicode!
        uri_query = urlparse.urlparse(uri).query

        signature_type, params = self.get_signature_type_and_params(uri_query,
            headers, body)

        # the parameters may not include duplicate oauth entries
        filtered_params = utils.filter_oauth_params(params)
        if len(filtered_params) != len(params):
            raise ValueError("Duplicate OAuth entries.")

        params = dict(params)
        request_signature = params.get(u'oauth_signature')
        client_key = params.get(u'oauth_consumer_key')
        resource_owner_key = params.get(u'oauth_token')
        nonce = params.get(u'oauth_nonce')
        timestamp = params.get(u'oauth_timestamp')
        callback_uri = params.get(u'oauth_callback')
        verifier = params.get(u'oauth_verifier')
        signature_method = params.get(u'oauth_signature_method')

        # ensure all mandatory parameters are present
        if not all((request_signature, client_key, nonce,
                    timestamp, signature_method)):
            raise ValueError("Missing OAuth parameters.")

        # if version is supplied, it must be "1.0"
        if u'oauth_version' in params and params[u'oauth_version'] != u'1.0':
            raise ValueError("Invalid OAuth version.")

        # signature method must be valid
        if not signature_method in SIGNATURE_METHODS:
            raise ValueError("Invalid signature method.")

        # ensure client key is valid
        if not self.check_client_key(client_key):
            return False

        # ensure resource owner key is valid and not expired
        if not self.check_resource_owner_key(client_key, resource_owner_key):
            return False

        # ensure the nonce and timestamp haven't been used before
        if not self.check_timestamp_and_nonce(timestamp, nonce):
            return False

        # FIXME: extract realm, then self.check_realm

        # oauth_client parameters depend on client chosen signature method
        # which may vary for each request, section 3.4
        # HMAC-SHA1 and PLAINTEXT share parameters
        if signature_method == SIGNATURE_RSA:
            oauth_client = Client(client_key,
                resource_owner_key=resource_owner_key,
                callback_uri=callback_uri,
                signature_method=signature_method,
                signature_type=signature_type,
                rsa_key=self.rsa_key, verifier=verifier)
        else:
            client_secret = self.get_client_secret(client_key)
            resource_owner_secret = self.get_resource_owner_secret(
                resource_owner_key)
            oauth_client = Client(client_key,
                client_secret=client_secret,
                resource_owner_key=resource_owner_key,
                resource_owner_secret=resource_owner_secret,
                callback_uri=callback_uri,
                signature_method=signature_method,
                signature_type=signature_type,
                verifier=verifier)

        request = Request(uri, http_method, body, headers)
        request.oauth_params = params

        client_signature = oauth_client.get_oauth_signature(request)

        # FIXME: use near constant time string compare to avoid timing attacks
        return client_signature == request_signature
