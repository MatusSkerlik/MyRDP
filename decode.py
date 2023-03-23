import zlib
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import List, Union

import cv2
import numpy as np

from dao import VideoData


class AbstractDecoderStrategy(ABC):
    @abstractmethod
    def decode_packet(self, video_data: VideoData) -> List[bytes]:
        pass


class DefaultDecoder(AbstractDecoderStrategy):
    class FrameType(IntEnum):
        FULL_FRAME = 0x01
        DIFF_FRAME = 0x02

    def __init__(self):
        self._last_frame: Union[None, np.ndarray] = None

    def decode_packet(self, video_data: VideoData) -> List[bytes]:
        width = video_data.get_width()
        height = video_data.get_height()
        frame_type = video_data.get_frame_type()
        data = video_data.get_data()
        frame = zlib.decompress(data)
        nframe = np.frombuffer(frame, dtype=np.uint8)
        nframe = nframe.reshape((width, height, 3))

        if frame_type == DefaultDecoder.FrameType.FULL_FRAME:
            self._last_frame = nframe
        elif frame_type == DefaultDecoder.FrameType.DIFF_FRAME and self._last_frame is not None:
            nframe = cv2.add(self._last_frame, nframe)
        else:
            raise RuntimeError("invalid frame type or not previous frame available")
        return [nframe]
