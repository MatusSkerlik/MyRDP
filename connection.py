import socket
from typing import Union


class NoDataAvailableError(Exception):
    """Custom exception class to represent no data being available to read."""


class NoConnection(Exception):
    """Custom exception class to represent that there is no connection with server and client."""
    pass


class Connection:
    MAX_PACKET_SIZE = 4096

    def __init__(self, local_ip: str, local_port: int, remote_ip: str, remote_port: int) -> None:
        super().__init__()

        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port

        # udp socket
        self.socket: Union[None, socket.socket] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((local_ip, local_port))

    def write(self, data: bytes) -> None:
        # Split data into smaller chunks
        chunks = [data[i:i + Connection.MAX_PACKET_SIZE] for i in range(0, len(data), Connection.MAX_PACKET_SIZE)]
        for chunk in chunks:
            self.socket.sendto(chunk, (self.remote_ip, self.remote_port))

    def read(self, bufsize: int) -> bytes:
        while True:
            buffer, remote = self.socket.recvfrom(bufsize)
            remote_ip, remote_port = remote
            if remote_ip == self.remote_ip and remote_port == remote_port:
                return buffer
