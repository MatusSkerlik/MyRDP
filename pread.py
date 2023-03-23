import io
import socket
import struct
import zlib

from dao import VideoData, AbstractDataObject
from enums import PacketType
from error import UnexpectedPacketTypeError


class BytesReader:
    def __init__(self, data: bytes):
        self.buffer = io.BytesIO(data)

    def read_int(self) -> int:
        """Read an integer from the buffer in big-endian format."""
        return struct.unpack('>I', self.buffer.read(4))[0]

    def read_string(self) -> str:
        """Read a string from the buffer by first reading its length, then reading the UTF-8 encoded string."""
        length = self.read_int()
        encoded_value = self.buffer.read(length)
        return encoded_value.decode('utf-8')

    def read_byte(self) -> int:
        """Read a byte from the buffer."""
        return struct.unpack('B', self.buffer.read(1))[0]

    def read_boolean(self) -> bool:
        """Read a boolean value from the buffer as a single byte (1 for True, 0 for False)."""
        return self.read_byte() == 1

    def read_bytes(self) -> bytes:
        """Read raw bytes from the buffer, prefixed with the length of the bytes as an integer."""
        length = self.read_int()
        return self.buffer.read(length)


class SocketDataReader(BytesReader):
    """
    SocketDataReader is responsible for reading packets from a socket and handling
    the logic of buffering, ensuring sufficient data for a packet, and parsing
    the packet based on its type.

    Args:
        sock: The socket object to read data from.
        buffer_size: The size of the buffer to read from the socket at once.
    """

    def __init__(self, sock: socket.socket, buffer_size: int = 4096):
        super().__init__(b"")  # Initialize BytesReader with empty bytes
        self._sock = sock
        self._buffer_size = buffer_size

    def _fill_buffer(self):
        """
        Reads data from the socket and appends it to the buffer.
        Raises a ConnectionError if the connection is closed.
        """
        data = self._sock.recv(self._buffer_size)
        if not data:
            raise ConnectionError("Connection closed")

        current_pos = self.buffer.tell()
        self.buffer.seek(0, io.SEEK_END)
        self.buffer.write(data)
        self.buffer.seek(current_pos)

    def _flush_read_data(self):
        """
        Flushes read data from the buffer by discarding the data read so far
        and leaving only the unread data in the buffer.
        """
        remaining_data = self.buffer.getvalue()[self.buffer.tell():]
        self.buffer = io.BytesIO()
        self.buffer.write(remaining_data)
        self.buffer.seek(0)

    def _ensure_data(self, size: int):
        """
        Ensures that the buffer has at least `size` bytes of data.
        """
        while self.buffer.getbuffer().nbytes < size:
            self._fill_buffer()

    def read_int(self) -> int:
        self._ensure_data(4)
        return super().read_int()

    def read_string(self) -> str:
        self._ensure_data(4)  # Length of the string
        length = super().read_int()
        self._ensure_data(length)
        return super().read_string()

    def read_byte(self) -> int:
        self._ensure_data(1)
        return super().read_byte()

    def read_boolean(self) -> bool:
        self._ensure_data(1)
        return super().read_boolean()

    def read_bytes(self) -> bytes:
        self._ensure_data(4)  # Length of the bytes
        length = super().read_int()
        self._ensure_data(length)
        return super().read_bytes()

    def read_packet(self) -> AbstractDataObject:
        """
        Reads a packet from the buffer and returns its content.
        Handles different packet types and raises an UnexpectedPacketTypeError
        if an unknown packet type is encountered.

        Returns:
            video_data (bytes): The video frame_packet contained in the packet.
        """
        try:
            packet_type = PacketType(self.read_byte())

            if packet_type == PacketType.VIDEO_DATA:

                width = self.read_int()
                height = self.read_int()
                frame_packet = self.read_bytes()

                # Seek to the start of frame packet, -4 represents byte array size
                self.buffer.seek(self.buffer.tell() - 1 - len(frame_packet) - 4)

                encoder_type = self.read_int()
                frame_type = self.read_int()
                compressed_data = self.read_bytes()
                encoded_frame = zlib.decompress(compressed_data)

                return VideoData(width, height, encoder_type, frame_type, encoded_frame)
            else:
                raise UnexpectedPacketTypeError(packet_type)
        finally:
            self._flush_read_data()
