import socket
import threading
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
        self.initialized = AutoLockingValue(False)
        self.socket: Union[None, socket.socket] = None

    def write(self, data: bytes) -> None:
        if self.running.getv():
            if self.initialized.getv():
                # Should never block, buffer have unlimited space
                def _run(data_):
                    try:
                        while len(data_) > 0:
                            try:
                                sent = self.socket.send(data_)
                                data_ = data[sent:]
                            except BlockingIOError:
                                time.sleep(0.0025)
                                continue
                    except OSError as e:
                        # Can happen when remote host closed connection
                        self.initialized.setv(False)
                        print(f"send error: {e}")
                    except AttributeError:
                        # Can happen when socket was set not None ( call to stop() method )
                        pass

                threading.Thread(target=_run, args=(data,)).start()
                return
            else:
                raise NoConnection("Connection is not established")
        else:
            raise RuntimeError("Connection stopped")

    def read(self, bufsize: int) -> bytes:
        if self.running.getv():
            try:
                if self.initialized.getv():
                    data = self.socket.recv(bufsize)
                    if data:
                        return data
                    else:
                        # EOF
                        raise OSError
                else:
                    raise NoConnection("Connection is not established")
            except BlockingIOError:
                # Can happen when there is no data available
                raise NoDataAvailableError
            except OSError as e:
                # Can happen when remote host closed connection
                self.initialized.setv(False)
                print(f"recv error: {e}")
                raise NoConnection(e)
        else:
            raise RuntimeError("Connection stopped")

    def stop(self):
        if self.socket:
            self.socket.close()
            self.socket = None

        # Join writing thread
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
        self._server_socket = None

    def run(self):
        while self.running.getv():

            if not self.initialized.getv():
                self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server_socket.bind((self._host, self._port))
                self._server_socket.listen(self._backlog)
                print(f"Listening on {self._host}:{self._port}")
                try:
                    self.socket, client_address = self._server_socket.accept()
                    self.socket.setblocking(False)
                except OSError as e:
                    self._server_socket.close()
                    self._server_socket = None
                    self.socket = None
                    print(f"Accept Error: {e}")
                    time.sleep(self._retry_timeout)
                    continue

                # Close server socket after obtaining client
                self._server_socket.close()
                self._server_socket = None

                # Pass all waiters for read and write calls
                self.initialized.setv(True)

                print(f"Connection from {client_address}")

            time.sleep(0.25)
        print(f"AutoReconnectServer worker thread exited")

    def stop(self):
        # If we are listening for connections, and we want to close the thread
        # Will raise OSError in thread
        if self._server_socket:
            self._server_socket.close()
        super().stop()


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
            if not self.initialized.getv():
                try:
                    print(f"Trying to connect to {self._host}:{self._port}")
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self._host, self._port))
                    self.socket.setblocking(False)
                    self.initialized.setv(True)
                    print(f"Connected to {self._host}:{self._port}")
                except OSError as e:
                    print(f"Connect error: {e}")
                    print(f"Retrying in {self._retry_timeout} seconds...")
                    time.sleep(self._retry_timeout)
            time.sleep(0.25)
        print(f"AutoReconnectClient worker thread exited")
