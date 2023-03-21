import io
import socket
import struct
from io import BytesIO

from dao import VideoData, AbstractDataObject
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
        self._sock = sock
        self._buffer_size = buffer_size
        self._buffer = BytesIO()

    def _fill_buffer(self):
        """
        Reads data from the socket and appends it to the buffer.
        Raises a ConnectionError if the connection is closed.
        """
        data = self._sock.recv(self._buffer_size)
        if not data:
            raise ConnectionError("Connection closed")

        current_pos = self._buffer.tell()
        self._buffer.seek(0, io.SEEK_END)
        self._buffer.write(data)
        self._buffer.seek(current_pos)

    def _flush_read_data(self):
        """
        Flushes read data from the buffer by discarding the data read so far
        and leaving only the unread data in the buffer.
        """
        remaining_data = self._buffer.getvalue()[self._buffer.tell():]
        self._buffer = io.BytesIO()
        self._buffer.write(remaining_data)
        self._buffer.seek(0)

    def _ensure_data(self, size: int):
        """
        Ensures that the buffer has at least `size` bytes of data.
        """
        while self._buffer.getbuffer().nbytes < size:
            self._fill_buffer()

    def read_int(self) -> int:
        """Read an integer from the buffer in big-endian format."""
        self._ensure_data(4)
        return struct.unpack('>I', self._buffer.read(4))[0]

    def read_string(self) -> str:
        """Read a string from the buffer by first reading its length, then reading the UTF-8 encoded string."""
        length = self.read_int()
        self._ensure_data(length)
        encoded_value = self._buffer.read(length)
        return encoded_value.decode('utf-8')

    def read_byte(self) -> int:
        """Read a byte from the buffer."""
        self._ensure_data(1)
        return struct.unpack('B', self._buffer.read(1))[0]

    def read_boolean(self) -> bool:
        """Read a boolean value from the buffer as a single byte (1 for True, 0 for False)."""
        return self.read_byte() == 1

    def read_bytes(self) -> bytes:
        """Read raw bytes from the buffer, prefixed with the length of the bytes as an integer."""
        length = self.read_int()
        self._ensure_data(length)
        return self._buffer.read(length)

    def read_packet(self) -> AbstractDataObject:
        """
        Reads a packet from the buffer and returns its content.
        Handles different packet types and raises an UnexpectedPacketTypeError
        if an unknown packet type is encountered.

        Returns:
            video_data (bytes): The video data contained in the packet.
        """
        try:
            packet_type = PacketType(self.read_byte())

            if packet_type == PacketType.VIDEO_DATA:

                width = self.read_int()
                height = self.read_int()
                data = self.read_bytes()
                return VideoData(width, height, data)
            else:
                raise UnexpectedPacketTypeError(packet_type)
        finally:
            self._flush_read_data()
