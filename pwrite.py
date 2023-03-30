import time

from connection import Connection
from packet import Packet
from pfactory import SynchronizationPacketFactory


class SocketDataWriter:
    """
    A class for writing data packets to a socket connection.

    Attributes:
        _connection (Connection): The connection object for the socket.
    """

    def __init__(self, connection: Connection, sync_packet_timeout=1):
        self._connection = connection
        self._sync_packet_timeout = sync_packet_timeout
        self._last_sync_packet = time.time()

    def write_packet(self, packet: Packet, block=True) -> None:
        if time.time() - self._last_sync_packet > self._sync_packet_timeout:
            self._last_sync_packet = time.time()
            self._connection.write(SynchronizationPacketFactory.create_packet().get_bytes(), block)
        self._connection.write(packet.get_bytes(), block)
