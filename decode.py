from abc import ABC, abstractmethod
import numpy as np
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import List, Optional, Any, Dict

from dao import VideoData


class AbstractDecoderStrategy(ABC):
    @abstractmethod
    def decode_packet(self, video_data: VideoData) -> List[bytes]:
        pass


class DefaultDecoder:
    class FrameType(IntEnum):
        FULL_FRAME = 0x01
        DIFF_FRAME = 0x02

    def __str__(self):
        return f"DefaultDecoder()"

    def decode_packet(self, video_data: VideoData) -> List[np.ndarray]:
        frame_type = video_data.get_frame_type()
        data = video_data.get_data()

        nframe = np.frombuffer(data, dtype=np.uint8)
        print(nframe)
        if frame_type == DefaultDecoder.FrameType.FULL_FRAME:
            return [nframe]
        else:
            raise RuntimeError("invalid frame type or not previous frame available")


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
