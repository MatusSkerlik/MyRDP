import socket
import threading
import time
from abc import ABC
from typing import Union

from lock import AutoLockingValue
from thread import Task


class NoDataAvailableError(Exception):
    """Custom exception class to represent no data being available to read."""


class Connection(Task, ABC):

    def __init__(self) -> None:
        super().__init__()

        self.running = AutoLockingValue(False)
        self.initialized = threading.Event()
        self.initialized.clear()
        self.socket: Union[None, socket.socket] = None

    def write(self, data: bytes, block=True) -> None:
        if self.running.getv():
            try:
                if self.initialized.wait(None if block else 0):
                    self.socket.setblocking(True)
                    self.socket.sendall(data)
                    return
            except OSError as e:
                # Can happen when remote host closed connection
                self.initialized.clear()
                self.socket.close()
                self.socket = None
                print(f"sendall error: {e}")
                raise ConnectionError(f"Connection not established: {e}")
            except AttributeError as e:
                # Can happen when server socket is None
                raise ConnectionError(f"Connection not established: {e}")
        else:
            raise RuntimeError("Connection stopped")

    def read(self, bufsize: int, block=True) -> bytes:
        if self.running.getv():
            try:
                if self.initialized.wait(None if block else 0):
                    self.socket.setblocking(False)
                    data = self.socket.recv(bufsize)
                    if data:
                        return data
                    else:
                        # EOF
                        raise OSError
            except BlockingIOError:
                # Can happen when there is no data available
                raise NoDataAvailableError
            except AttributeError as e:
                # Can happen when socket is None
                raise ConnectionError(f"Connection not established: {e}")
            except OSError as e:
                # Can happen when remote host closed connection
                self.initialized.clear()
                self.socket.close()
                self.socket = None
                print(f"recv error: {e}")
                raise ConnectionError(e)
        else:
            raise RuntimeError("Connection stopped")

    def stop(self):
        if isinstance(self.socket, socket.socket):
            self.socket.close()
            self.socket = None
        # Free waiters
        self.initialized.set()

        super().stop()


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

            if not self.initialized.is_set():
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Block this loop max _retry_timeout
                server_socket.bind((self._host, self._port))
                server_socket.listen(self._backlog)
                server_socket.settimeout(self._retry_timeout)

                try:
                    self.socket, client_address = server_socket.accept()
                except OSError as e:
                    server_socket.close()
                    print(f"Accept Error: {e}")
                    continue

                # Close server socket after obtaining client
                server_socket.close()

                # Pass all waiters for read and write calls
                self.initialized.set()

                print(f"Connection from {client_address}")

            time.sleep(self._retry_timeout)


class AutoReconnectClient(Connection):
    """
    A client-side connection that automatically attempts to reconnect
    to the server when disconnected.

    Attributes:
        host (str): The server's hostname or IP address.
        port (int): The server's port number.
        retry_interval (int): The time interval between reconnection attempts.
    """

    def __init__(self, host: str, port: int, retry_interval=0.5):
        super().__init__()
        self._host = host
        self._port = port
        self._retry_interval = retry_interval

    def run(self):
        while self.running.getv():
            if not self.initialized.is_set():
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.settimeout(self._retry_interval)
                    self.socket.connect((self._host, self._port))
                    self.initialized.set()
                    print(f"Connected to {self._host}:{self._port}")
                except OSError as e:
                    print(f"Connect error: {e}")
                    print(f"Retrying in {self._retry_interval} seconds...")
                    self.initialized.clear()
                    self.socket.close()
                    self.socket = None
                    continue
            time.sleep(self._retry_interval)
