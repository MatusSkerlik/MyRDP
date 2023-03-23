from abc import ABC

from packet import Packet
from pfactory import VideoContainerDataPacketFactory


class AbstractDataObject(ABC):
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
