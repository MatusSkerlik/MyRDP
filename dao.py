from abc import ABC

from packet import Packet
from pfactory import VideoDataPacketFactory


class AbstractDataObject(ABC):
    pass


class VideoData(AbstractDataObject):
    def __init__(self, width: int, height: int, data: bytes):
        self._width = width
        self._height = height
        self._data = data

    def get_packet(self) -> Packet:
        return VideoDataPacketFactory.create_packet(self._width, self._height, self._data)

    def get_bytes(self) -> bytes:
        return self.get_packet().get_bytes()

    def get_width(self):
        return self._width

    def get_height(self):
        return self._height

    def get_data(self):
        return self._data
