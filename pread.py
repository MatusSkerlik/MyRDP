import io
import struct
from typing import Union

from connection import Connection
from dao import VideoData, AbstractDataObject
from enums import PacketType


class InvalidPacketType(Exception):
    pass


class BytesReader:
    def __init__(self, data: bytes):
        self.buffer = io.BytesIO(data)

    def read_int(self) -> int:
        """Read an integer from the buffer in big-endian format."""
        return struct.unpack('>I', self.buffer.read(4))[0]

    def read_string(self, length: int) -> str:
        """Read a string from the buffer by first reading its length, then reading the UTF-8 encoded string."""
        encoded_value = self.buffer.read(length)
        return encoded_value.decode('utf-8')

    def read_byte(self) -> int:
        """Read a byte from the buffer."""
        return struct.unpack('B', self.buffer.read(1))[0]

    def read_boolean(self) -> bool:
        """Read a boolean value from the buffer as a single byte (1 for True, 0 for False)."""
        return self.read_byte() == 1

    def read_bytes(self, length: int) -> bytes:
        """Read raw bytes from the buffer, prefixed with the length of the bytes as an integer."""
        return self.buffer.read(length)


class SocketDataReader(BytesReader):
    def __init__(self, connection: Connection, buffer_size: int = 4096):
        super().__init__(b"")  # Initialize BytesReader with empty bytes
        self._buffer_size = buffer_size
        self._connection = connection

    def _fill_buffer(self):
        """
        Reads data from the socket and appends it to the buffer.
        Raises a ConnectionError if the connection is closed.
        """
        data = self._connection.read(self._buffer_size)

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

    def read_string(self, **kwargs) -> str:
        self._ensure_data(4)  # Length of the string
        length = super().read_int()
        self._ensure_data(length)
        return super().read_string(length)

    def read_byte(self) -> int:
        self._ensure_data(1)
        return super().read_byte()

    def read_boolean(self) -> bool:
        self._ensure_data(1)
        return super().read_boolean()

    def read_bytes(self, **kwargs) -> bytes:
        self._ensure_data(4)  # Length of the bytes
        length = super().read_int()
        self._ensure_data(length)
        return super().read_bytes(length)

    def read_packet(self) -> Union[None, AbstractDataObject]:
        try:
            try:
                packet_type = PacketType(self.read_byte())
            except ValueError:
                # This error indicates, that reset should be made
                raise InvalidPacketType

            if packet_type == PacketType.VIDEO_DATA:
                width = self.read_int()
                height = self.read_int()
                frame_packet = self.read_bytes()

                # Seek to the start of frame packet, -4 represents byte array size
                self.buffer.seek(self.buffer.tell() - len(frame_packet))

                encoder_type = self.read_int()
                frame_type = self.read_int()
                encoded_frame = self.read_bytes()

                self._flush_read_data()

                return VideoData(width, height, encoder_type, frame_type, encoded_frame)

            raise NotImplementedError
        except ConnectionError:
            # Connection lost, reset buffer
            self.buffer = io.BytesIO()
