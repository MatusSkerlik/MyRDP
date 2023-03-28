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


class DefaultDecoder:
    class FrameType(IntEnum):
        FULL_FRAME = 0x01
        DIFF_FRAME = 0x02

    def __init__(self):
        self._last_frame: Union[None, cv2.UMat] = None

    def __str__(self):
        return f"DefaultDecoder()"

    def decode_packet(self, video_data: VideoData) -> List[np.ndarray]:
        width = video_data.get_width()
        height = video_data.get_height()
        frame_type = video_data.get_frame_type()
        data = video_data.get_data()

        try:
            frame = zlib.decompress(data)
        except zlib.error as e:
            # TODO why is zlib.error happening and how to prevent it
            print(e)
            return [self._last_frame]
        nframe = np.frombuffer(frame, dtype=np.uint8)
        nframe = cv2.UMat(nframe.reshape((width, height, 3)))

        if frame_type == DefaultDecoder.FrameType.FULL_FRAME:
            self._last_frame = nframe
        elif frame_type == DefaultDecoder.FrameType.DIFF_FRAME and self._last_frame is not None:
            nframe = cv2.add(self._last_frame, nframe)
        else:
            raise RuntimeError("invalid frame type or not previous frame available")
        return [nframe.get()]


class DecoderStrategyBuilder:
    """
    A builder class for creating EncoderStrategy objects.

    This builder class allows you to easily create EncoderStrategy objects by
    specifying the strategy type and any options needed for the strategy.

    Example:
        builder = DecoderStrategyBuilder()
        decoder_strategy = builder.set_strategy_type("default").build()
    """

    def __init__(self) -> None:
        self._strategy_type: Optional[str] = None
        self._options: Dict[str, Any] = {}

    def set_strategy_type(self, strategy_type: str) -> "DecoderStrategyBuilder":
        self._strategy_type = strategy_type
        return self

    def set_option(self, key: str, value: Any) -> "DecoderStrategyBuilder":
        self._options[key] = value
        return self

    def build(self) -> AbstractDecoderStrategy:
        if not self._strategy_type:
            raise ValueError

        if self._strategy_type.lower() == "default":
            return DefaultDecoder()

        # Add other strategy types here
        raise NotImplementedError
