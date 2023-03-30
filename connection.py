import socket
import threading
import time
from abc import ABC, abstractmethod
from typing import Union

from lock import AutoLockingValue


class Connection(ABC):

    @abstractmethod
    def write(self, data: bytes, block: bool) -> None:
        pass

    @abstractmethod
    def read(self, bufsize: int, block: bool) -> bytes:
        pass


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
        self._host = host
        self._port = port
        self._backlog = backlog
        self._retry_timeout = retry_timeout
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._client_socket = None
        self._client_connected = threading.Event()
        self._accept_thread: Union[None, threading.Thread] = None
        self._running = AutoLockingValue(False)

    def write(self, data: bytes, block=True) -> None:
        if self._running.getv():
            try:
                if self._client_connected.wait(None if block else 0):
                    self._client_socket.sendall(data)
                    return
            except socket.timeout as e:
                print(f"Socket sendall error: {e}")
            except socket.error as e:
                self._client_connected.clear()
                print(f"Socket sendall error: {e}")
        raise ConnectionError

    def read(self, bufsize: int, block=True) -> bytes:
        if self._running.getv():
            try:
                if self._client_connected.wait(None if block else 0):
                    return self._client_socket.recv(bufsize)
            except socket.timeout as e:
                print(f"Socket recv error: {e}")
            except socket.error as e:
                self._client_connected.clear()
                print(f"Socket recv error: {e}")
        raise ConnectionError

    def start(self):
        self._running.setv(True)
        self._bind()
        if self._accept_thread is None:
            self._accept_thread = threading.Thread(target=self._accept)
            self._accept_thread.daemon = True
            self._accept_thread.start()
        else:
            raise RuntimeError("Thread already started.")

    def stop(self):
        self._running.setv(False)

        self._client_socket.close()
        # Raise throw in accept thread
        self._server_socket.close()
        # Finalize
        self._accept_thread.join()
        self._accept_thread = None
        # Unblock all waiters
        self._client_connected.set()

    def _bind(self):
        try:
            self._server_socket.setblocking(True)
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(self._backlog)
            print(f"Server listening on {self._host}:{self._port}")
        except socket.error as e:
            print(f"Bind error: {e}")
            self._server_socket.close()
            self._server_socket = None
            raise e

    def _accept(self):
        while self._running.getv():
            if not self._client_connected.is_set():
                try:
                    client_socket, client_address = self._server_socket.accept()
                    self._client_socket = client_socket
                    self._client_socket.setblocking(True)
                    self._client_connected.set()
                    print(f"Connection from {client_address}")
                except socket.error as e:
                    self._client_connected.clear()
                    print(f"Accept error: {e}")
            else:
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

    def __init__(self, host, port, retry_interval=1):
        self._host = host
        self._port = port
        self._retry_interval = retry_interval
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_connected = threading.Event()
        self._connect_thread: Union[None, threading.Thread] = None
        self._running = AutoLockingValue(False)

    def write(self, data: bytes, block=True) -> None:
        if self._running.getv():
            try:
                if self._server_connected.wait(None if block else 0):
                    self._server_socket.sendall(data)
            except socket.timeout as e:
                print(f"Socket sendall error: {e}")
            except socket.error as e:
                self._server_connected.clear()
                print(f"Socket sendall error: {e}")
        raise ConnectionError

    def read(self, bufsize: int, block=True) -> bytes:
        if self._running.getv():
            try:
                if self._server_connected.wait(None if block else 0):
                    return self._server_socket.recv(bufsize)
            except socket.timeout as e:
                print(f"Socket recv error: {e}")
            except socket.error as e:
                self._server_connected.clear()
                print(f"Socket recv error: {e}")
        raise ConnectionError

    def start(self):
        self._running.setv(True)

        if self._connect_thread is None:
            self._connect_thread = threading.Thread(target=self._connect)
            self._connect_thread.daemon = True
            self._connect_thread.start()
        else:
            raise RuntimeError("Thread already started.")

    def stop(self):
        self._running.setv(False)

        # Raise throw in _connect method
        self._server_socket.close()

        # Finalize
        self._connect_thread.join()
        self._connect_thread = None

        # Unblock all waiters
        self._server_connected.set()

    def _connect(self):
        while self._running.getv():
            if not self._server_connected.is_set():
                try:
                    self._server_socket.connect((self._host, self._port))
                    self._server_socket.setblocking(True)
                    self._server_connected.set()
                    print(f"Connected to {self._host}:{self._port}")
                except socket.error as e:
                    print(f"Connect error: {e}")
                    print(f"Retrying in {self._retry_interval} seconds...")
                    self._server_connected.clear()
                    time.sleep(self._retry_interval)
            else:
                time.sleep(self._retry_interval)
