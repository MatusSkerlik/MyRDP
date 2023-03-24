import zlib
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import List, Union, Optional, Any, Dict

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

    def decode_packet(self, video_data: VideoData) -> List[np.ndarray]:
        width = video_data.get_width()
        height = video_data.get_height()
        frame_type = video_data.get_frame_type()
        data = video_data.get_data()
        try:
            frame = zlib.decompress(data)
        except zlib.error as e:
            if self._last_frame is not None:
                return [self._last_frame]
            else:
                raise e
        nframe = np.frombuffer(frame, dtype=np.uint8)
        nframe = nframe.reshape((width, height, 3))

        if frame_type == DefaultDecoder.FrameType.FULL_FRAME:
            self._last_frame = nframe
        elif frame_type == DefaultDecoder.FrameType.DIFF_FRAME and self._last_frame is not None:
            nframe = cv2.add(self._last_frame, nframe)
        else:
            raise RuntimeError("invalid frame type or not previous frame available")
        return [nframe]


class DecoderStrategyBuilder:

    def __init__(self) -> None:
        self._strategy_type: Optional[str] = None
        self._options: Dict[str, Any] = {}

    def set_strategy_type(self, strategy_type: str) -> "DecoderStrategyBuilder":
        self._strategy_type = strategy_type
        return self

    def set_option(self, key: str, value: Any) -> "DecoderStrategyBuilder":
        self._options[key] = value
        return self

    def build(self) -> Union[None, AbstractDecoderStrategy]:
        if not self._strategy_type:
            return None

        if self._strategy_type.lower() == "default":
            return DefaultDecoder()

        # Add other strategy types here
        return None
