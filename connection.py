import io
import socket
import time
from abc import ABC, abstractmethod
from typing import Union

from lock import AutoLockingValue
from thread import Task


class NoDataAvailableError(Exception):
    """Custom exception class to represent no data being available to read."""


class NoConnection(Exception):
    """Custom exception class to represent that there is no connection with server and client."""
    pass


class IOStream:

    def has_exception(self) -> bool:
        return self.get_exception() is not None

    @abstractmethod
    def get_exception(self) -> Exception:
        pass


class InputStream(Task, IOStream):

    def __init__(self, sock: socket.socket) -> None:
        super().__init__()

        self._socket = sock
        self._socket.setblocking(False)

        self._buffer = io.BytesIO()
        self._closed = False
        self._eof = False
        self._exception = None
        self.start()

    def get_exception(self):
        return self._exception

    def is_closed(self):
        return self._closed

    def is_eof(self):
        return self._eof

    def read(self) -> bytes:
        try:
            return self._buffer.getvalue()
        finally:
            self._flush()

    def run(self):
        while self.running.getv():
            try:
                data = self._socket.recv(4096)
                if data != b'':
                    self._buffer.write(data)
                else:
                    # Socket closed by remote
                    self._close(eof=True)
            except BlockingIOError:
                # This line is what makes me mad
                time.sleep(0.0025)
            except OSError as e:
                self._close(eof=False)
                self._exception = e

    def _close(self, eof: bool):
        self._closed = True
        self._eof = eof
        self.stop()

    def _flush(self):
        self._buffer = io.BytesIO()


class OutputStream(Task, IOStream):

    def __init__(self, sock: socket.socket) -> None:
        super().__init__()

        self._socket = sock
        self._socket.setblocking(False)

        self._buffer = io.BytesIO()
        self._closed = False
        self._exception = None
        self.start()

    def get_exception(self):
        return self._exception

    def is_closed(self):
        return self._closed

    def write(self, data: bytes) -> None:
        if self._buffer.write(data) != len(data):
            raise RuntimeError

    def run(self):
        while self.running.getv():
            try:
                while len(self._buffer.getvalue()) > 0:
                    sent = self._socket.send(self._buffer.getvalue())
                    self._flush(sent)
            except BlockingIOError:
                # This line is what makes me mad
                time.sleep(0.0025)
            except OSError as e:
                self._close()
                self._exception = e

    def _close(self):
        self._closed = True
        self.stop()

    def _flush(self, sent: int):
        remaining_data = self._buffer.getvalue()[sent:]
        self._buffer = io.BytesIO()
        self._buffer.write(remaining_data)
        self._buffer.seek(0)


class Connection(Task, ABC):

    def __init__(self) -> None:
        super().__init__()

        self.connected = AutoLockingValue(False)
        self.socket: Union[None, socket.socket] = None
        self._input_stream = None
        self._output_stream = None

    def get_input_stream(self) -> Union[None, InputStream]:
        if self.connected.getv():
            if self._input_stream is None or self._input_stream.has_exception():
                self._input_stream = InputStream(self.socket)
            return self._input_stream
        return None

    def get_output_stream(self) -> Union[None, OutputStream]:
        if self.connected.getv():
            if self._output_stream is None or self._output_stream.has_exception():
                self._output_stream = OutputStream(self.socket)
            return self._output_stream
        return None

    def stop(self):
        if self.socket:
            self.socket.close()
            self.socket = None

        # Join connection establishing threads
        super().stop()

    def is_connected(self):
        return self.connected.getv()


class AutoReconnectServer(Connection):
    """
    A server-side connection that automatically attempts to reconnect
    when a client disconnects.

    Attributes:
        host (str): The server's hostname or IP address.
        port (int): The server's port number.
        backlog (int): The maximum number of queued connections.
        retry_timeout (int): The time interval between connection attempts.
    """

    def __init__(self, host: str, port: int, backlog=1, retry_timeout=1):
        super().__init__()

        self._host = host
        self._port = port
        self._backlog = backlog
        self._retry_timeout = retry_timeout

    def run(self):
        while self.running.getv():
            if not self.connected.getv():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:

                    server_socket.bind((self._host, self._port))
                    server_socket.listen(self._backlog)

                    print(f"Listening on {self._host}:{self._port}")

                    try:
                        self.socket, client_address = server_socket.accept()

                        # enable keepalive option
                        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                        # set the keepalive interval (in seconds)
                        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)

                        # set the number of keepalive probes
                        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

                        # set the interval between keepalive probes (in seconds)
                        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)

                    except OSError as e:
                        self.socket = None
                        print(f"Accept Error: {e}")
                        time.sleep(self._retry_timeout)
                        continue

                    # Pass all waiters for read and write calls
                    self.connected.setv(True)

                    print(f"Connection from {client_address}")

            time.sleep(0.25)


class AutoReconnectClient(Connection):
    """
    A client-side connection that automatically attempts to reconnect
    to the server when disconnected.

    Attributes:
        host (str): The server's hostname or IP address.
        port (int): The server's port number.
        retry_interval (int): The time interval between reconnection attempts.
    """

    def __init__(self, host: str, port: int, retry_timeout=1):
        super().__init__()
        self._host = host
        self._port = port
        self._retry_timeout = retry_timeout

    def run(self):
        while self.running.getv():
            if not self.connected.getv():
                try:
                    print(f"Trying to connect to {self._host}:{self._port}")
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self._host, self._port))
                    self.connected.setv(True)
                    print(f"Connected to {self._host}:{self._port}")
                except OSError as e:
                    print(f"Connect error: {e}")
                    print(f"Retrying in {self._retry_timeout} seconds...")
                    time.sleep(self._retry_timeout)
            time.sleep(0.25)
