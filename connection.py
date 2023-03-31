import socket
import threading
import time
from abc import ABC
from typing import Union, Callable

from lock import AutoLockingValue


class Connection(ABC):

    def __init__(self, runnable: Callable) -> None:
        self.running = AutoLockingValue(False)
        self.initialized = threading.Event()
        self.initialized.clear()
        self.socket: Union[None, socket.socket] = None
        self.thread: Union[None, threading.Thread] = threading.Thread(target=runnable)
        self.thread.daemon = True

    def write(self, data: bytes, block=True) -> None:
        if self.running.getv():
            try:
                if self.initialized.wait(None if block else 0):
                    self.socket.sendall(data)
                    return
            except socket.timeout as e:
                # Can happen when socket has timeout set and
                # operation could not finish in time
                raise ConnectionError(e)
            except socket.error as e:
                self.initialized.clear()
                print(f"Socket sendall error: {e}")
                raise ConnectionError(e)
            except AttributeError as e:
                # Can happen when server socket is initializing
                raise ConnectionError(e)
        raise ConnectionError("Connection closed")

    def read(self, bufsize: int, block=True) -> bytes:
        if self.running.getv():
            try:
                if self.initialized.wait(None if block else 0):
                    return self.socket.recv(bufsize)
            except socket.timeout as e:
                # Can happen when socket has timeout set and
                # operation could not finish in time
                raise ConnectionError(e)
            except socket.error as e:
                self.initialized.clear()
                print(f"recv error: {e}")
                raise ConnectionError(e)
            except AttributeError as e:
                # Can happen when server socket is initializing
                raise ConnectionError(e)
        raise ConnectionError("Connection closed")

    def start(self):
        self.running.setv(True)
        self.thread.start()

    def stop(self):
        self.running.setv(False)
        if isinstance(self.socket, socket.socket):
            self.socket.close()
        # Free waiters
        self.initialized.set()
        # self.thread.join()


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

    def __init__(self, host, port, backlog=1, retry_timeout=1):
        super().__init__(self._accept)

        self._host = host
        self._port = port
        self._backlog = backlog
        self._retry_timeout = retry_timeout

    def _accept(self):
        while True:
            time.sleep(0.01)
            with self.running as is_running:
                if not is_running:
                    break

                if not self.initialized.is_set():
                    try:
                        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        server_socket.settimeout(1)
                        server_socket.bind((self._host, self._port))
                        server_socket.listen(self._backlog)
                        if self.socket is not None:
                            self.socket.close()
                        self.socket, client_address = server_socket.accept()
                        self.socket.setblocking(True)
                        self.initialized.set()

                        # Close server socket after obtaining client
                        server_socket.close()
                        print(f"Connection from {client_address}")
                    except socket.timeout:
                        continue
                    except socket.error as e:
                        self.initialized.clear()
                        print(f"Accept error: {e}")
                elif self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) != 0:
                    # There is error with socket
                    self.initialized.clear()


class AutoReconnectClient(Connection):
    """
    A client-side connection that automatically attempts to reconnect
    to the server when disconnected.

    Attributes:
        host (str): The server's hostname or IP address.
        port (int): The server's port number.
        retry_interval (int): The time interval between reconnection attempts.
    """

    def __init__(self, host, port, retry_interval=1):
        super().__init__(self._connect)
        self._host = host
        self._port = port
        self._retry_interval = retry_interval

    def _connect(self):
        while True:
            time.sleep(0.01)
            with self.running as is_running:
                if not is_running:
                    break

                if not self.initialized.is_set():
                    try:
                        if self.socket is not None:
                            self.socket.close()
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket.connect((self._host, self._port))
                        self.socket.setblocking(True)
                        self.initialized.set()
                        print(f"Connected to {self._host}:{self._port}")
                    except socket.timeout:
                        continue
                    except socket.error as e:
                        print(f"Connect error: {e}")
                        print(f"Retrying in {self._retry_interval} seconds...")
                        self.initialized.clear()
                        time.sleep(self._retry_interval)
                elif self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) != 0:
                    # There is error with socket
                    self.initialized.clear()
