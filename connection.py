import socket
import threading
import time
from abc import ABC, abstractmethod
from typing import Union

from lock import AutoLockingValue


class Connection(ABC):

    @abstractmethod
    def write(self, data: bytes) -> None:
        pass

    @abstractmethod
    def read(self, bufsize: int) -> bytes:
        pass


class ReconnectingServerConnection(Connection):
    def __init__(self, host, port, backlog=1):
        self._host = host
        self._port = port
        self._backlog = backlog
        self._server_socket: Union[None, socket.socket] = None
        self._client_socket: AutoLockingValue[Union[None, socket.socket]] = AutoLockingValue(None)
        self._client_socket_set = threading.Event()
        self._accept_thread: Union[None, threading.Thread] = None
        self._exiting = AutoLockingValue(False)

    def write(self, data: bytes) -> None:
        try:
            self._client_socket_set.wait()
            with self._client_socket as sock:
                if isinstance(sock, socket.socket):
                    sock.sendall(data)
        except socket.error as e:
            self._client_socket_set.clear()
            print(f"Socket sendall error: {e}")

    def read(self, bufsize: int) -> Union[None, bytes]:
        try:
            self._client_socket_set.wait()
            # Client socket can be null when stop is called
            with self._client_socket as sock:
                if isinstance(sock, socket.socket):
                    return sock.recv(bufsize)
                else:
                    return None
        except socket.error as e:
            self._client_socket_set.clear()
            print(f"Socket recv error: {e}")

    def start(self):
        self._bind()
        if self._accept_thread is None:
            self._accept_thread = threading.Thread(target=self._accept)
            self._accept_thread.daemon = True
            self._accept_thread.start()
        else:
            raise RuntimeError("Thread already started.")

    def stop(self):
        self._client_socket.get().close()
        self._client_socket.set(None)
        # Raise throw in accept thread
        self._server_socket.close()
        self._server_socket = None
        # Finalize
        self._accept_thread.join()
        self._accept_thread = None
        # Unblock all waiters
        self._client_socket_set.set()

    def _bind(self):
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(self._backlog)
            print(f"Server listening on {self._host}:{self._port}")
        except socket.error as e:
            print(f"Bind error: {e}")
            self._server_socket.close()
            self._server_socket = None
            raise e

    def _accept(self):
        while True:
            try:
                client_socket, client_address = self._server_socket.accept()
                self._client_socket: AutoLockingValue[Union[None, socket.socket]] = AutoLockingValue(client_socket)
                self._client_socket_set.set()
                print(f"Connection from {client_address}")
            except socket.error as e:
                self._client_socket_set.clear()
                self._client_socket.set(None)
                print(f"Accept error: {e}")


class ReconnectingClientConnection(Connection):
    def __init__(self, host, port, retry_interval=1):
        self._host = host
        self._port = port
        self._retry_interval = retry_interval
        self._server_socket: AutoLockingValue[Union[None, socket.socket]] = AutoLockingValue(None)
        self._server_socket_set = threading.Event()
        self._connect_thread: Union[None, threading.Thread] = None

    def write(self, data: bytes) -> None:
        try:
            self._server_socket_set.wait()
            with self._server_socket as sock:
                if isinstance(sock, socket.socket):
                    sock.sendall(data)
        except socket.error as e:
            self._server_socket_set.clear()
            print(f"Socket sendall error: {e}")

    def read(self, bufsize: int) -> Union[None, bytes]:
        try:
            self._server_socket_set.wait()
            with self._server_socket as sock:
                if isinstance(sock, socket.socket):
                    return sock.recv(bufsize)
                else:
                    return None
        except socket.error as e:
            self._server_socket_set.clear()
            print(f"Socket recv error: {e}")

    def start(self):
        if self._connect_thread is None:
            self._connect_thread = threading.Thread(target=self._connect)
            self._connect_thread.daemon = True
            self._connect_thread.start()
        else:
            raise RuntimeError("Thread already started.")

    def stop(self):
        # Raise throw in thread if connect is called
        self._server_socket.get().close()
        self._server_socket.set(None)
        # Finalize
        self._connect_thread.join()
        self._connect_thread = None
        # Unblock all waiters
        self._server_socket_set.set()

    def _connect(self):
        while True:
            if not self._server_socket_set.is_set():
                try:
                    self._server_socket: AutoLockingValue[Union[None, socket.socket]] = AutoLockingValue(
                        socket.socket(socket.AF_INET, socket.SOCK_STREAM))
                    self._server_socket.get().connect((self._host, self._port))
                    self._server_socket_set.set()
                    print(f"Connected to {self._host}:{self._port}")
                except socket.error as e:
                    self._server_socket_set.clear()
                    print(f"Connect error: {e}")
                    print(f"Retrying in {self._retry_interval} seconds...")
                    time.sleep(self._retry_interval)
            else:
                time.sleep(self._retry_interval)
