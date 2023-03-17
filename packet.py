import io
import struct


class Packet:
    def __init__(self) -> None:
        """Initialize a new Packet object with an empty buffer."""
        self.buffer = io.BytesIO()

    def add_int(self, value: int) -> None:
        """
        Add an integer to the packet buffer in big-endian format.

        Args:
            value: The integer value to add to the buffer.
        """
        self.buffer.write(struct.pack('>I', value))

    def add_string(self, value: str) -> None:
        """
        Add a string to the packet buffer by encoding it in UTF-8 and
        prefixing it with the length of the encoded string in big-endian format.

        Args:
            value: The string value to add to the buffer.
        """
        encoded_value = value.encode('utf-8')
        self.add_int(len(encoded_value))
        self.buffer.write(encoded_value)

    def add_byte(self, value: int) -> None:
        """
        Add a byte to the packet buffer.

        Args:
            value: The byte value to add to the buffer.
        """
        self.buffer.write(struct.pack('B', value))

    def add_boolean(self, value: bool) -> None:
        """
        Add a boolean value to the packet buffer as a single byte (1 for True, 0 for False).

        Args:
            value: The boolean value to add to the buffer.
        """
        self.add_byte(1 if value else 0)

    def add_bytes(self, value: bytes) -> None:
        """
        Add raw bytes to the packet buffer, prefixed with the length of the bytes as an integer.

        Args:
            value: The bytes value to add to the buffer.
        """
        self.add_int(len(value))
        self.buffer.write(value)

    def get_bytes(self) -> bytes:
        """
        Return the current contents of the packet buffer as bytes.

        Returns:
            A bytes object containing the contents of the buffer.
        """
        return self.buffer.getvalue()

    def clear(self) -> None:
        """Clear the packet buffer by creating a new empty buffer."""
        self.buffer = io.BytesIO()
