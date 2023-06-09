import socket
import time
from abc import ABC
from typing import Union

from lock import AutoLockingValue
from thread import Task


class NoDataAvailableError(Exception):
    """Custom exception class to represent no data being available to read."""


class NoConnection(Exception):
    """Custom exception class to represent that there is no connection with server and client."""
    pass


class Connection(Task, ABC):

    def __init__(self) -> None:
        super().__init__()

        self.running = AutoLockingValue(False)
        self.connected = AutoLockingValue(False)
        self.socket: Union[None, socket.socket] = None

    def write(self, data: bytes) -> None:
        if self.running.getv():
            if self.connected.getv():
                try:
                    self.socket.sendall(data)
                except OSError as e:
                    self.connected.setv(False)
                    print(f"sendall error {e}")
                    raise NoConnection(e)
                return
            else:
                raise NoConnection("Connection is not established")
        else:
            raise RuntimeError("Connection stopped")

    def read(self, bufsize: int) -> bytes:
        if self.running.getv():
            try:
                if self.connected.getv():
                    data = self.socket.recv(bufsize)
                    if data != b'':
                        return data
                    else:
                        # Socket closed by remote
                        raise OSError
                else:
                    raise NoConnection("Connection is not established")
            except OSError as e:
                # Can happen when remote host closed connection
                self.connected.setv(False)
                print(f"recv error: {e}")
                raise NoConnection(e)
        else:
            raise RuntimeError("Connection stopped")

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
        self._server_socket = None

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
