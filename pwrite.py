import socket

from packet import Packet


class SocketDataWriter:
    def __init__(self, sock: socket.socket):
        self._socket = sock

    def write_packet(self, packet: Packet) -> None:
        """
        Send a packet to the connected socket.
        :param packet: The packet data to be sent as bytes.
        """
        self._socket.sendall(packet.get_bytes())
