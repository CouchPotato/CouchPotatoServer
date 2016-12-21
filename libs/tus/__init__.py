import os
import base64
import logging
import argparse

import requests

LOG_LEVEL = logging.INFO
DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024
TUS_VERSION = '1.0.0'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.NullHandler())


class TusError(Exception):
    pass


def _init():
    fmt = "[%(asctime)s] %(levelname)s %(message)s"
    h = logging.StreamHandler()
    h.setLevel(LOG_LEVEL)
    h.setFormatter(logging.Formatter(fmt))
    logger.addHandler(h)


def _create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=argparse.FileType('rb'))
    parser.add_argument('--chunk-size', type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument(
        '--header',
        action='append',
        help="A single key/value pair"
        " to be sent with all requests as HTTP header."
        " Can be specified multiple times to send more then one header."
        " Key and value must be separated with \":\".")
    return parser


def _cmd_upload():
    _init()

    parser = _create_parser()
    parser.add_argument('tus_endpoint')
    parser.add_argument('--file_name')
    parser.add_argument(
        '--metadata',
        action='append',
        help="A single key/value pair to be sent in Upload-Metadata header."
        " Can be specified multiple times to send more than one pair."
        " Key and value must be separated with space.")
    args = parser.parse_args()

    headers = dict([x.split(':') for x in args.header])
    metadata = dict([x.split(' ') for x in args.metadata])

    upload(
        args.file,
        args.tus_endpoint,
        chunk_size=args.chunk_size,
        file_name=args.file_name,
        headers=headers,
        metadata=metadata)


def _cmd_resume():
    _init()

    parser = _create_parser()
    parser.add_argument('file_endpoint')
    args = parser.parse_args()

    headers = dict([x.split(':') for x in args.header])

    resume(
        args.file,
        args.file_endpoint,
        chunk_size=args.chunk_size,
        headers=headers)


def upload(file_obj,
           tus_endpoint,
           chunk_size=DEFAULT_CHUNK_SIZE,
           file_name=None,
           headers=None,
           metadata=None):
    file_name = os.path.basename(file_obj.name)
    file_size = _get_file_size(file_obj)
    location = _create_file(
        tus_endpoint,
        file_name,
        file_size,
        extra_headers=headers,
        metadata=metadata)
    resume(
        file_obj, location, chunk_size=chunk_size, headers=headers, offset=0)


def _get_file_size(f):
    pos = f.tell()
    f.seek(0, 2)
    size = f.tell()
    f.seek(pos)
    return size


def _create_file(tus_endpoint,
                 file_name,
                 file_size,
                 extra_headers=None,
                 metadata=None):
    logger.info("Creating file endpoint")

    headers = {
        "Tus-Resumable": TUS_VERSION,
        "Upload-Length": str(file_size),
    }

    if extra_headers:
        headers.update(extra_headers)

    if metadata:
        l = [k + ' ' + base64.b64encode(v) for k, v in metadata.items()]
        headers["Upload-Metadata"] = ','.join(l)

    response = requests.post(tus_endpoint, headers=headers)
    if response.status_code != 201:
        raise TusError("Create failed: %s" % response)

    location = response.headers["Location"]
    logger.info("Created: %s", location)
    return location


def resume(file_obj,
           file_endpoint,
           chunk_size=DEFAULT_CHUNK_SIZE,
           headers=None,
           offset=None):
    if offset is None:
        offset = _get_offset(file_endpoint, extra_headers=headers)

    total_sent = 0
    file_size = _get_file_size(file_obj)
    while offset < file_size:
        file_obj.seek(offset)
        data = file_obj.read(chunk_size)
        offset = _upload_chunk(
            data, offset, file_endpoint, extra_headers=headers)
        total_sent += len(data)
        logger.info("Total bytes sent: %i", total_sent)


def _get_offset(file_endpoint, extra_headers=None):
    logger.info("Getting offset")

    headers = {"Tus-Resumable": TUS_VERSION}

    if extra_headers:
        headers.update(extra_headers)

    response = requests.head(file_endpoint, headers=headers)
    response.raise_for_status()

    offset = int(response.headers["Upload-Offset"])
    logger.info("offset=%i", offset)
    return offset


def _upload_chunk(data, offset, file_endpoint, extra_headers=None):
    logger.info("Uploading chunk from offset: %i", offset)

    headers = {
        'Content-Type': 'application/offset+octet-stream',
        'Upload-Offset': str(offset),
        'Tus-Resumable': TUS_VERSION,
    }

    if extra_headers:
        headers.update(extra_headers)

    response = requests.patch(file_endpoint, headers=headers, data=data)
    if response.status_code != 204:
        raise TusError("Upload chunk failed: %s" % response)

    return int(response.headers["Upload-Offset"])
