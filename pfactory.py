from abc import abstractmethod, ABC

from packet import Packet
from enums import PacketType, ASCIIEnum, ButtonState


class AbstractPacketFactory(ABC):

    @staticmethod
    @abstractmethod
    def create_packet(*args, **kwargs) -> Packet:
        """
        Create a packet based on the factory type.
        """
        pass


class MouseClickAbstractPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(button, state, x, y) -> Packet:
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
    def create_packet(x, y) -> Packet:
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


class VideoDataPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(frame_data) -> Packet:
        """
        Create a video data packet.

        Args:
            frame_data: The raw video data (compressed or encoded) as bytes.
        """
        packet = Packet()
        packet.add_byte(PacketType.VIDEO_DATA)
        packet.add_int(len(frame_data))
        packet.add_bytes(frame_data)
        return packet


class KeyboardEventAbstractPacketFactory(AbstractPacketFactory):

    @staticmethod
    def create_packet(key_code: ASCIIEnum, state: ButtonState) -> Packet:
        """
        Create a keyboard event packet.

        Args:
            key_code: The key code of the keyboard event.
            state: The key state (e.g., PRESS, RELEASE).
        """
        packet = Packet()
        packet.add_byte(PacketType.KEYBOARD_EVENT)
        packet.add_int(key_code)
        packet.add_byte(state)
        return packet
