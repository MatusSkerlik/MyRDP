from connection import Connection
from packet import Packet


class SocketDataWriter:
    def __init__(self, connection: Connection):
        self._connection = connection

    def write_packet(self, packet: Packet, block=True) -> None:
        self._connection.write(packet.get_bytes(), block)
