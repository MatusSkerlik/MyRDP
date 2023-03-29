from abc import ABC, abstractmethod

from enums import MouseButton, ButtonState, ASCIIEnum
from packet import Packet
from pfactory import VideoContainerDataPacketFactory, MouseMovePacketFactory, MouseClickPacketFactory, \
    KeyboardEventPacketFactory


class AbstractDataObject(ABC):

    @abstractmethod
    def to_packet(self) -> Packet:
        pass


class VideoData(AbstractDataObject):
    def __init__(self, width: int, height: int, encoder_type: int, frame_type: int, data: bytes):
        self._width = width
        self._height = height
        self._encoder_type = encoder_type
        self._frame_type = frame_type
        self._data = data

    def to_packet(self) -> Packet:
        return VideoContainerDataPacketFactory.create_packet(self._width, self._height, self._data)

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def get_encoder_type(self) -> int:
        return self._encoder_type

    def get_frame_type(self) -> int:
        return self._frame_type

    def get_data(self) -> bytes:
        return self._data


class MouseMoveData(AbstractDataObject):
    def __init__(self, x: int, y: int):
        self._x = x
        self._y = y

    def to_packet(self) -> Packet:
        return MouseMovePacketFactory.create_packet(self._x, self.y)

    def get_x(self):
        return self._x

    def get_y(self):
        return self._y


class MouseClickData(AbstractDataObject):

    def __init__(self, x: int, y: int, button: MouseButton, state: ButtonState) -> None:
        self._x = x
        self._y = y
        self._button = button
        self._state = state

    def to_packet(self) -> Packet:
        return MouseClickPacketFactory.create_packet(self._x, self._y, self._button, self._state)

    def get_x(self):
        return self._x

    def get_y(self):
        return self._y

    def get_button(self):
        return self._button

    def get_state(self):
        return self._state


class KeyboardData(AbstractDataObject):
    def __init__(self, key: ASCIIEnum, state: ButtonState):
        self._key = key
        self._state = state

    def to_packet(self) -> Packet:
        return KeyboardEventPacketFactory.create_packet(self._key, self._state)

    def get_key(self):
        return self._key

    def get_state(self):
        return self._state
