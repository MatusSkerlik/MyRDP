import socket
from io import BytesIO

from enums import PacketType
from error import UnexpectedPacketTypeError


class SocketDataReader:
    """
    SocketDataReader is responsible for reading packets from a socket and handling
    the logic of buffering, ensuring sufficient data for a packet, and parsing
    the packet based on its type.

    Args:
        sock: The socket object to read data from.
        buffer_size: The size of the buffer to read from the socket at once.
    """

    def __init__(self, sock: socket.socket, buffer_size: int = 4096):
        self.sock = sock
        self.buffer_size = buffer_size
        self.buffer = BytesIO()

    def _fill_buffer(self):
        """
        Reads data from the socket and appends it to the buffer.
        Raises a ConnectionError if the connection is closed.
        """
        data = self.sock.recv(self.buffer_size)
        if not data:
            raise ConnectionError("Connection closed")
        self.buffer.write(data)

    def _ensure_data(self, size: int):
        """
        Ensures that the buffer has at least `size` bytes of data.
        """
        while self.buffer.tell() < size:
            self._fill_buffer()

    def read_packet(self):
        """
        Reads a packet from the buffer and returns its content.
        Handles different packet types and raises an UnexpectedPacketTypeError
        if an unknown packet type is encountered.

        Returns:
            video_data (bytes): The video data contained in the packet.
        """
        self._ensure_data(1)  # Packet type is 1 byte
        packet_type = PacketType(self.buffer.read(1)[0])

        if packet_type == PacketType.VIDEO_DATA:
            self._ensure_data(4)  # Size of video data length is 4 bytes
            video_data_length = int.from_bytes(self.buffer.read(4), byteorder='little')

            self._ensure_data(video_data_length)
            video_data = self.buffer.read(video_data_length)
            return video_data
        else:
            raise UnexpectedPacketTypeError(packet_type)
