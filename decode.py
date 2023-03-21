import zlib
from abc import ABC, abstractmethod
from typing import List, Union

import numpy as np


class AbstractDecoderStrategy(ABC):
    @abstractmethod
    def decode_packet(self, width: int, height: int, packet_data: bytes) -> List[bytes]:
        pass


class DefaultDecoder(AbstractDecoderStrategy):
    def __init__(self):
        self._prev_frame: Union[None, np.ndarray] = None

    def decode_packet(self, width: int, height: int, packet_data: bytes) -> List[bytes]:
        frame = zlib.decompress(packet_data)
        frame = np.frombuffer(frame, dtype=np.uint8)
        frame = frame.reshape((width, height, 3))
