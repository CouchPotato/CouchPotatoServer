"""A synchronous implementation of the Deluge RPC protocol
   based on gevent-deluge by Christopher Rosell.
   
   https://github.com/chrippa/gevent-deluge

Example usage:

    from synchronousdeluge import DelgueClient

    client = DelugeClient()
    client.connect()

    # Wait for value
    download_location = client.core.get_config_value("download_location").get()
"""


__title__ = "synchronous-deluge"
__version__ = "0.1"
__author__ = "Christian Dale"

from synchronousdeluge.client import DelugeClient
from synchronousdeluge.exceptions import DelugeRPCError

