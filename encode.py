import zlib
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional, Any, Dict, Union

import cv2
import numpy as np

from pfactory import VideoFrameDataPacketFactory


class AbstractEncoderStrategy(ABC):
    ID: int

    @abstractmethod
    def encode_frame(self, width: int, height: int, frame: bytes):
        pass


class DefaultEncoder(AbstractEncoderStrategy):
    ID = 0x01

    class FrameType(IntEnum):
        FULL_FRAME = 0x01
        DIFF_FRAME = 0x02

    def __init__(self, fps: int) -> None:
        self._fps = fps

        self._last_frame: Union[None, np.ndarray] = None
        self._frame_count = 0

    def encode_frame(self, width: int, height: int, frame: bytes) -> bytes:
        nframe = np.frombuffer(frame, dtype=np.uint8)
        nframe.reshape((width, height, 3))

        self._last_frame = nframe
        if self._frame_count % self._fps == 0:
            self._frame_count = 1
            compressed_frame = zlib.compress(nframe.tobytes())
            packet = VideoFrameDataPacketFactory.create_packet(DefaultEncoder.ID,
                                                               DefaultEncoder.FrameType.FULL_FRAME,
                                                               compressed_frame)
            return packet.get_bytes()
        else:
            self._frame_count += 1
            diff = cv2.absdiff(self._last_frame, nframe)
            mask = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
            _, mask = cv2.threshold(mask, 30, 255, cv2.THRESH_BINARY)
            diff_data = cv2.bitwise_and(frame, frame, mask=mask)
            compressed_frame = zlib.compress(diff_data.tobytes())
            packet = VideoFrameDataPacketFactory.create_packet(DefaultEncoder.ID,
                                                               DefaultEncoder.FrameType.DIFF_FRAME,
                                                               compressed_frame)
            return packet.get_bytes()


class EncoderStrategyBuilder:
    """
    A builder class for creating EncoderStrategy objects.

    This builder class allows you to easily create EncoderStrategy objects by
    specifying the strategy type and any options needed for the strategy.

    Example:
        builder = EncoderStrategyBuilder()
        encoder_strategy = (builder.set_strategy_type("av")
                                  .set_option("width", 1280)
                                  .set_option("height", 720)
                                  .build())
    """

    def __init__(self) -> None:
        self._strategy_type: Optional[str] = None
        self._options: Dict[str, Any] = {}

    def set_strategy_type(self, strategy_type: str) -> "EncoderStrategyBuilder":
        self._strategy_type = strategy_type
        return self

    def set_option(self, key: str, value: Any) -> "EncoderStrategyBuilder":
        self._options[key] = value
        return self

    def build(self) -> Optional[AbstractEncoderStrategy]:
        if not self._strategy_type:
            return None

        if self._strategy_type.lower() == "default":
            fps = self._options.get("fps", 30)
            return DefaultEncoder(fps)

        # Add other strategy types here
        return None
