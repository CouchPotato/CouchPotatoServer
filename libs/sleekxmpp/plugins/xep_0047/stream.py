import socket
import threading
import logging

from sleekxmpp.util import Queue
from sleekxmpp.exceptions import XMPPError


log = logging.getLogger(__name__)


class IBBytestream(object):

    def __init__(self, xmpp, sid, block_size, to, ifrom, window_size=1):
        self.xmpp = xmpp
        self.sid = sid
        self.block_size = block_size
        self.window_size = window_size

        self.receiver = to
        self.sender = ifrom

        self.send_seq = -1
        self.recv_seq = -1

        self._send_seq_lock = threading.Lock()
        self._recv_seq_lock = threading.Lock()

        self.stream_started = threading.Event()
        self.stream_in_closed = threading.Event()
        self.stream_out_closed = threading.Event()

        self.recv_queue = Queue()

        self.send_window = threading.BoundedSemaphore(value=self.window_size)
        self.window_ids = set()
        self.window_empty = threading.Event()
        self.window_empty.set()

    def send(self, data):
        if not self.stream_started.is_set() or \
               self.stream_out_closed.is_set():
            raise socket.error
        data = data[0:self.block_size]
        self.send_window.acquire()
        with self._send_seq_lock:
            self.send_seq = (self.send_seq + 1) % 65535
            seq = self.send_seq
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['to'] = self.receiver
        iq['from'] = self.sender
        iq['ibb_data']['sid'] = self.sid
        iq['ibb_data']['seq'] = seq
        iq['ibb_data']['data'] = data
        self.window_empty.clear()
        self.window_ids.add(iq['id'])
        iq.send(block=False, callback=self._recv_ack)
        return len(data)

    def sendall(self, data):
        sent_len = 0
        while sent_len < len(data):
            sent_len += self.send(data[sent_len:])

    def _recv_ack(self, iq):
        self.window_ids.remove(iq['id'])
        if not self.window_ids:
            self.window_empty.set()
        self.send_window.release()
        if iq['type'] == 'error':
            self.close()

    def _recv_data(self, iq):
        with self._recv_seq_lock:
            new_seq = iq['ibb_data']['seq']
            if new_seq != (self.recv_seq + 1) % 65535:
                self.close()
                raise XMPPError('unexpected-request')
            self.recv_seq = new_seq

        data = iq['ibb_data']['data']
        if len(data) > self.block_size:
            self.close()
            raise XMPPError('not-acceptable')

        self.recv_queue.put(data)
        self.xmpp.event('ibb_stream_data', {'stream': self, 'data': data})
        iq.reply()
        iq.send()

    def recv(self, *args, **kwargs):
        return self.read(block=True)

    def read(self, block=True, timeout=None, **kwargs):
        if not self.stream_started.is_set() or \
               self.stream_in_closed.is_set():
            raise socket.error
        if timeout is not None:
            block = True
        try:
            return self.recv_queue.get(block, timeout)
        except:
            return None

    def close(self):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['to'] = self.receiver
        iq['from'] = self.sender
        iq['ibb_close']['sid'] = self.sid
        self.stream_out_closed.set()
        iq.send(block=False,
                callback=lambda x: self.stream_in_closed.set())
        self.xmpp.event('ibb_stream_end', self)

    def _closed(self, iq):
        self.stream_in_closed.set()
        self.stream_out_closed.set()
        while not self.window_empty.is_set():
            log.info('waiting for send window to empty')
            self.window_empty.wait(timeout=1)
        iq.reply()
        iq.send()
        self.xmpp.event('ibb_stream_end', self)

    def makefile(self, *args, **kwargs):
        return self

    def connect(*args, **kwargs):
        return None

    def shutdown(self, *args, **kwargs):
        return None
