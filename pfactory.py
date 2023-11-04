from abc import ABC, abstractmethod

from constants import SYNC_SEQUENCE
from enums import PacketType, MouseButton, ButtonState
from packet import Packet


class AbstractPacketFactory(ABC):

    @staticmethod
    @abstractmethod
    def create_packet(*args, **kwargs) -> Packet:
        """
        Create a packet based on the factory type.
        """
        pass


class MouseClickPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(x: int, y: int, button: MouseButton, state: ButtonState) -> Packet:
        """
        Create a mouse click packet.

        Args:
            button: The button identifier (e.g., LEFT, MIDDLE, RIGHT).
            state: The button state (e.g., PRESS, RELEASE).
            x: The x-coordinate of the mouse click.
            y: The y-coordinate of the mouse click.
        """
        packet = Packet()
        packet.add_byte(PacketType.MOUSE_CLICK)
        packet.add_byte(button)
        packet.add_byte(state)
        packet.add_int(x)
        packet.add_int(y)
        return packet


class MouseMovePacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(x: int, y: int) -> Packet:
        """
        Create a mouse move packet.

        Args:
            x: The x-coordinate of the mouse position.
            y: The y-coordinate of the mouse position.
        """
        packet = Packet()
        packet.add_byte(PacketType.MOUSE_MOVE)
        packet.add_int(x)
        packet.add_int(y)
        return packet


class KeyboardEventPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(key_code: str, state: ButtonState) -> Packet:
        """
        Create a keyboard event packet.

        Args:
            key_code: The key code of the keyboard event.
            state: The key state (e.g., PRESS, RELEASE).
        """
        packet = Packet()
        packet.add_byte(PacketType.KEYBOARD_EVENT)
        packet.add_string(key_code)
        packet.add_byte(state)
        return packet


class VideoContainerDataPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(width: int, height: int, data: bytes) -> Packet:
        """
        Create a video container packet.

        Args:
            width: The width of video frame/s encoded in data
            height: The height of video frame/s encoded in data
            data: The raw video data (compressed or encoded) as bytes.
        """
        packet = Packet()
        packet.add_byte(PacketType.VIDEO_DATA)
        packet.add_int(width)
        packet.add_int(height)
        packet.add_bytes(data)
        return packet


class VideoFrameDataPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(encoder_type: int, frame_type: int, data: bytes) -> Packet:
        """
        Create a video frame packet.
        Args:
            encoder_type: type of encoder which created this packet
            frame_type: type of frame which is encoded in this frame
            data: actual encoded data of frame
        """
        packet = Packet()
        packet.add_int(encoder_type)
        packet.add_int(frame_type)
        packet.add_bytes(data)
        return packet


class SynchronizationPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(*args, **kwargs) -> Packet:
        """
        Creates a new synchronization packet.

        The packet contains the synchronization byte sequence
        """
        packet = Packet()
        packet.add_byte(PacketType.SYNC)
        packet.add_bytes(SYNC_SEQUENCE)
        return packet
