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


class ReconnectingServerConnection(Connection):
    def __init__(self, host, port, backlog=1, retry_timeout=1):
        self._host = host
        self._port = port
        self._backlog = backlog
        self._retry_timeout = retry_timeout
        self._server_socket = socket.socket()
        self._client_socket: AutoLockingValue[socket.socket] = AutoLockingValue(socket.socket())
        self._client_socket_set = threading.Event()
        self._accept_thread: Union[None, threading.Thread] = None
        self._running = AutoLockingValue(False)

    def write(self, data: bytes, block=True) -> None:
        if self._running.get():
            try:
                if block:
                    self._client_socket_set.wait()
                with self._client_socket as sock:
                    sock.sendall(data)
                    return
            except socket.error as e:
                self._client_socket_set.clear()
                print(f"Socket sendall error: {e}")
        raise ConnectionError

    def read(self, bufsize: int, block=True) -> Union[None, bytes]:
        if self._running.get():
            try:
                if block:
                    self._client_socket_set.wait()
                with self._client_socket as sock:
                    return sock.recv(bufsize)
            except socket.error as e:
                self._client_socket_set.clear()
                print(f"Socket recv error: {e}")
        raise ConnectionError

    def start(self):
        self._running.set(True)
        self._bind()
        if self._accept_thread is None:
            self._accept_thread = threading.Thread(target=self._accept)
            self._accept_thread.daemon = True
            self._accept_thread.start()
        else:
            raise RuntimeError("Thread already started.")

    def stop(self):
        self._running.set(False)

        self._client_socket.get().close()
        # Raise throw in accept thread
        self._server_socket.close()
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
        while self._running.get():
            if not self._client_socket_set.is_set():
                try:
                    print("Listening for new connection")
                    client_socket, client_address = self._server_socket.accept()
                    self._client_socket: AutoLockingValue[Union[None, socket.socket]] = AutoLockingValue(client_socket)
                    self._client_socket_set.set()
                    print(f"Connection from {client_address}")
                except socket.error as e:
                    print(f"Accept error: {e}")
            else:
                time.sleep(self._retry_timeout)


class ReconnectingClientConnection(Connection):
    def __init__(self, host, port, retry_interval=1):
        self._host = host
        self._port = port
        self._retry_interval = retry_interval
        self._server_socket: AutoLockingValue[socket.socket] = AutoLockingValue(socket.socket())
        self._server_socket_set = threading.Event()
        self._connect_thread: Union[None, threading.Thread] = None
        self._running = AutoLockingValue(False)

    def write(self, data: bytes, block=True) -> None:
        if self._running.get():
            try:
                if block:
                    self._server_socket_set.wait()
                with self._server_socket as sock:
                    sock.sendall(data)
                    return
            except socket.error as e:
                self._server_socket_set.clear()
                print(f"Socket sendall error: {e}")
        raise ConnectionError

    def read(self, bufsize: int, block=True) -> Union[None, bytes]:
        if self._running.get():
            try:
                if block:
                    self._server_socket_set.wait()
                with self._server_socket as sock:
                    return sock.recv(bufsize)
            except socket.error as e:
                self._server_socket_set.clear()
                print(f"Socket recv error: {e}")
        raise ConnectionError

    def start(self):
        self._running.set(True)

        if self._connect_thread is None:
            self._connect_thread = threading.Thread(target=self._connect)
            self._connect_thread.daemon = True
            self._connect_thread.start()
        else:
            raise RuntimeError("Thread already started.")

    def stop(self):
        self._running.set(False)

        # Raise throw in thread if connect is called
        self._server_socket.get().close()
        # Unblock all waiters
        self._server_socket_set.set()
        # Finalize
        self._connect_thread.join()

    def _connect(self):
        while self._running.get():
            if not self._server_socket_set.is_set():
                try:
                    self._server_socket: AutoLockingValue[Union[None, socket.socket]] = AutoLockingValue(
                        socket.socket(socket.AF_INET, socket.SOCK_STREAM))
                    self._server_socket.get().settimeout(self._retry_interval)
                    self._server_socket.get().connect((self._host, self._port))
                    self._server_socket_set.set()
                    print(f"Connected to {self._host}:{self._port}")
                except socket.error as e:
                    print(f"Connect error: {e}")
                    print(f"Retrying in {self._retry_interval} seconds...")
                    time.sleep(self._retry_interval)
            else:
                time.sleep(self._retry_interval)
